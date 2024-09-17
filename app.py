import os
import pandas as pd
import re
import unicodedata
import streamlit as st
from crawl4ai import WebCrawler
from crawl4ai.crawler_strategy import LocalSeleniumCrawlerStrategy
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from openai import OpenAI
from io import BytesIO
from urllib.parse import urlparse
import logging
import subprocess
import requests
import zipfile
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI Client
openai_client = OpenAI(
    api_key=st.secrets["openai_api_key"],  # Original key storage
)

# Function to download Chromium
def download_chromium(download_url, extract_path):
    try:
        st.info("🔄 Downloading Chromium...")
        response = requests.get(download_url, stream=True)
        zip_path = os.path.join(extract_path, "chromium.zip")
        with open(zip_path, "wb") as f:
            shutil.copyfileobj(response.raw, f)
        st.info("📥 Chromium downloaded successfully.")
        
        st.info("📦 Extracting Chromium...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        st.info("📂 Chromium extracted successfully.")
        
        # Clean up the zip file
        os.remove(zip_path)
        
        # Return the path to the Chromium binary
        chromium_binary = os.path.join(extract_path, "chrome-linux", "chrome")
        if not os.path.exists(chromium_binary):
            raise FileNotFoundError("Chromium binary not found after extraction.")
        
        return chromium_binary
    except Exception as e:
        logger.error(f"Error downloading or extracting Chromium: {e}")
        st.error(f"🔴 Error downloading or extracting Chromium: {e}")
        return None

# Function to verify Chromium and Chromedriver installations
def verify_installations(chromium_path, chromedriver_path):
    st.subheader("🔍 Installation Verification")
    
    st.write("### Chromium Browser")
    try:
        chrome_version = subprocess.check_output([chromium_path, '--version']).decode('utf-8').strip()
        st.code(chrome_version)
    except Exception as e:
        st.error(f"🔴 Error verifying Chromium installation: {e}")
        return False
    
    st.write("### Chromedriver")
    try:
        driver_version = subprocess.check_output([chromedriver_path, '--version']).decode('utf-8').strip()
        st.code(driver_version)
    except Exception as e:
        st.error(f"🔴 Error verifying Chromedriver installation: {e}")
        return False
    
    st.write("### Chromium Binary Location")
    st.code(chromium_path)
    
    st.write("### Chromedriver Binary Location")
    st.code(chromedriver_path)
    
    st.success("🟢 **Chromium** and **Chromedriver** are installed correctly.")
    return True

# Utility function to clean text
def clean_text(text):
    """
    Cleans the input text by normalizing unicode characters, removing non-printable characters,
    and eliminating specific unwanted symbols.
    """
    if not isinstance(text, str):
        return text
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    # Remove non-printable characters
    text = ''.join(c for c in text if c.isprintable())
    # Remove specific unwanted symbols (e.g., (TM), â€)
    text = re.sub(r'\(TM\)', '', text)
    text = re.sub(r'â€', '', text)
    # Remove any remaining unwanted characters or symbols
    text = re.sub(r'[^\x00-\x7F]+', '', text)  # Remove non-ASCII characters
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# Function to extract linkworthy items
def extract_linkworthy_items(scraped_content):
    """
    Uses OpenAI API to extract linkworthy items (ingredients and other affiliate-linkable items)
    from scraped content. Returns a plaintext string of items or "n/a" if extraction fails.
    """
    prompt = (
        "Extract all ingredients and any other items that can be used for affiliate linking "
        "from the following content. Present the results as a comma-separated plaintext list."
    )

    # Combine prompt with scraped content
    full_prompt = f"{prompt}\n\nContent:\n{scraped_content}"

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Ensure this model is available
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=500,
            n=1,
            stop=None,
            temperature=0.5,
        )

        # Extract the assistant's reply
        extracted_data = response.choices[0].message.content.strip()

        # Clean the extracted text
        cleaned_data = clean_text(extracted_data)

        # Check if extraction returned meaningful data
        if not cleaned_data:
            return "n/a"

        return cleaned_data

    except Exception as e:
        st.warning(f"⚠️ Error during OpenAI API call for linkworthy items: {e}")
        logger.error(f"OpenAI API Error for linkworthy items: {e}")
        return "n/a"

# Function to extract title
def extract_title(scraped_content):
    """
    Uses OpenAI API to extract the title from scraped content.
    Returns the title as plaintext or "n/a" if extraction fails.
    """
    prompt = (
        "Extract the title of the article from the following content. "
        "Present the result as a single plaintext string."
    )

    # Combine prompt with scraped content
    full_prompt = f"{prompt}\n\nContent:\n{scraped_content}"

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Ensure this model is available
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=100,
            n=1,
            stop=None,
            temperature=0.3,
        )

        # Extract the assistant's reply
        extracted_title = response.choices[0].message.content.strip()

        # Clean the extracted title
        cleaned_title = clean_text(extracted_title)

        # Check if extraction returned meaningful data
        if not cleaned_title:
            return "n/a"

        return cleaned_title

    except Exception as e:
        st.warning(f"⚠️ Error during OpenAI API call for title: {e}")
        logger.error(f"OpenAI API Error for title: {e}")
        return "n/a"

# Function to parse pasted URLs
def parse_pasted_urls(urls_text):
    """
    Parses a string of URLs separated by commas, newlines, or spaces.
    Returns a list of cleaned URLs.
    """
    # Split by comma, newline, or space
    urls = re.split(r'[,\n\s]+', urls_text)
    # Remove empty strings and strip whitespace
    urls = [url.strip() for url in urls if url.strip()]
    return urls

# Function to validate URLs
def is_valid_url(url):
    """
    Validates the URL format.
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

# Streamlit App
def main():
    st.title("🔗 URL Processor and Data Extractor")

    st.markdown("""
    ### 📄 Upload a CSV, Enter URLs Manually, or Paste a List of URLs
    - **Upload CSV**: Provide a CSV file with a 'URL' column.
    - **Manual Entry**: Enter URLs one-by-one.
    - **Paste List**: Paste a list of URLs separated by commas, newlines, or spaces.
    """)

    # Download Chromium
    chromium_download_url = "https://commondatastorage.googleapis.com/chromium-browser-snapshots/Linux_x64/1170697/chrome-linux.zip"  # Update to a stable version
    extract_path = "/tmp/chromium"  # Temporary directory
    if not os.path.exists(extract_path):
        os.makedirs(extract_path)
    chromium_binary = download_chromium(chromium_download_url, extract_path)
    if not chromium_binary:
        st.error("🔴 Failed to download and extract Chromium.")
        return

    # Use webdriver-manager to install chromedriver
    try:
        st.info("🔄 Installing Chromedriver via webdriver-manager...")
        chromedriver_path = ChromeDriverManager().install()
        st.success(f"✅ Chromedriver installed at: {chromedriver_path}")
    except Exception as e:
        logger.error(f"Error installing Chromedriver: {e}")
        st.error(f"🔴 Error installing Chromedriver: {e}")
        return

    # Verify installations
    verification_success = verify_installations(chromium_binary, chromedriver_path)
    if not verification_success:
        st.error("🔴 Chromium or Chromedriver is not installed correctly.")
        return

    # Configure Selenium to run Chromium in headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.binary_location = chromium_binary

    # Initialize Crawl4AI WebCrawler with LocalSeleniumCrawlerStrategy
    try:
        service = Service(chromedriver_path)  # Specify Chromedriver path
        webdriver_instance = webdriver.Chrome(service=service, options=chrome_options)
        
        crawler_strategy = LocalSeleniumCrawlerStrategy(driver=webdriver_instance)
        crawler = WebCrawler(verbose=False, crawler_strategy=crawler_strategy)
        crawler.warmup()
        logger.info("🟢 Selenium WebDriver initialized successfully.")
        st.success("🟢 Selenium WebDriver initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing Selenium WebDriver: {e}")
        st.error(f"🔴 Selenium initialization error: {e}")
        return

    # Initialize session state for failed URLs
    if 'failed_urls' not in st.session_state:
        st.session_state.failed_urls = []

    # File uploader for CSV
    uploaded_file = st.file_uploader("📁 Upload CSV with 'URL' column", type=["csv"])

    # Manual entry
    st.subheader("🖊️ Or Enter URLs Manually")
    manual_url = st.text_input("Enter a single URL")

    # Paste list of URLs
    st.subheader("📋 Or Paste a List of URLs")
    pasted_urls = st.text_area("Paste your URLs here (separated by commas, newlines, or spaces)")

    # Button to start processing
    if st.button("🚀 Process URLs"):
        urls = []

        # Handle uploaded CSV
        if uploaded_file is not None:
            try:
                df_input = pd.read_csv(uploaded_file)
                if 'URL' not in df_input.columns:
                    st.error("❌ CSV file must contain a 'URL' column.")
                else:
                    uploaded_urls = df_input['URL'].dropna().tolist()
                    # Validate URLs
                    valid_uploaded_urls = [url for url in uploaded_urls if is_valid_url(url)]
                    invalid_uploaded_urls = [url for url in uploaded_urls if not is_valid_url(url)]
                    urls.extend(valid_uploaded_urls)
                    st.success(f"✅ Loaded {len(valid_uploaded_urls)} valid URLs from the uploaded CSV.")
                    if invalid_uploaded_urls:
                        st.warning(f"⚠️ {len(invalid_uploaded_urls)} invalid URLs were skipped from the uploaded CSV.")
            except Exception as e:
                st.error(f"❌ Error reading CSV file: {e}")

        # Handle manual entry
        if manual_url:
            if is_valid_url(manual_url):
                urls.append(manual_url)
                st.success("✅ Added manually entered URL.")
            else:
                st.warning("⚠️ The manually entered URL is invalid and was skipped.")

        # Handle pasted URLs
        if pasted_urls:
            parsed_urls = parse_pasted_urls(pasted_urls)
            valid_pasted_urls = [url for url in parsed_urls if is_valid_url(url)]
            invalid_pasted_urls = [url for url in parsed_urls if not is_valid_url(url)]
            urls.extend(valid_pasted_urls)
            st.success(f"✅ Added {len(valid_pasted_urls)} valid URLs from pasted list.")
            if invalid_pasted_urls:
                st.warning(f"⚠️ {len(invalid_pasted_urls)} invalid URLs were skipped from the pasted list.")

        if not urls:
            st.error("❌ No valid URLs provided. Please upload a CSV, enter URLs manually, or paste a list of URLs.")
            return

        # Remove duplicates
        urls = list(dict.fromkeys(urls))
        st.write(f"📊 **Total unique valid URLs to process:** {len(urls)}")

        # Initialize lists for DataFrame
        data = {
            'Headline': [],
            'URL': [],
            'Linkworthy Ingredients': []
        }

        # Initialize progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Process each URL
        for idx, url in enumerate(urls):
            status_text.text(f"🔄 Processing URL {idx + 1} of {len(urls)}")
            try:
                # Scrape the webpage
                scrape_result = crawler.run(url=url, bypass_cache=True)

                if scrape_result.success:
                    content = scrape_result.extracted_content
                    if not content:
                        st.warning(f"⚠️ Scraped content is empty for URL: {url}")
                        linkworthy = "n/a"
                        title = "n/a"
                    else:
                        # Extract linkworthy items
                        linkworthy = extract_linkworthy_items(content)
                        if not linkworthy:
                            linkworthy = "n/a"

                        # Extract title
                        title = extract_title(content)
                        if not title:
                            title = "n/a"
                else:
                    st.warning(f"⚠️ Failed to scrape the URL: {url}")
                    linkworthy = "n/a"
                    title = "n/a"
                    st.session_state.failed_urls.append(url)

                # Append data
                data['Headline'].append(title)
                data['URL'].append(url)
                data['Linkworthy Ingredients'].append(linkworthy)

            except Exception as e:
                st.warning(f"⚠️ An error occurred while processing URL {url}: {e}")
                data['Headline'].append("n/a")
                data['URL'].append(url)
                data['Linkworthy Ingredients'].append("n/a")
                st.session_state.failed_urls.append(url)

            # Update progress bar
            progress = (idx + 1) / len(urls)
            progress_bar.progress(progress)

        # Create DataFrame
        df_output = pd.DataFrame(data)

        # Display the updated DataFrame
        st.subheader("📊 Processed Data")
        st.dataframe(df_output)

        # Prepare CSV for download
        csv_buffer = BytesIO()
        df_output.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        st.download_button(
            label="📥 Download data as CSV",
            data=csv_buffer,
            file_name='processed_data.csv',
            mime='text/csv',
        )

        # Display failed URLs if any
        if st.session_state.failed_urls:
            st.subheader("❗ Failed URLs")
            for failed_url in st.session_state.failed_urls:
                st.write(failed_url)

if __name__ == "__main__":
    main()
