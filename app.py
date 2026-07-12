import re
import requests
import streamlit as st
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


st.set_page_config(page_title="Server-Side URL Preview", page_icon="🌐")
st.title("🌐 Url Check From US IP")
st.markdown("Enter a website URL and the app will fetch and preview it from the server hosted in US loaction.")


def normalize_url(raw_url: str) -> str:
    candidate = raw_url.strip()
    if not candidate:
        raise ValueError("Please enter a URL.")

    if re.match(r"^https?://", candidate, re.IGNORECASE):
        parsed = urlparse(candidate)
    else:
        parsed = urlparse(f"https://{candidate}")

    if not parsed.scheme or not parsed.netloc:
        raise ValueError("That URL is not valid.")

    return parsed.geturl()


def fetch_page_from_server(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ServerPreviewBot/1.0; +https://example.com)"
    }
    response = requests.get(url, headers=headers, timeout=25, allow_redirects=True)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response


def get_server_country() -> str:
    try:
        ip_response = requests.get("https://api.ipify.org?format=json", timeout=10)
        ip_response.raise_for_status()
        ip = ip_response.json().get("ip")
        if not ip:
            return "Unknown"

        country_response = requests.get("https://ipinfo.io/json", timeout=10)
        country_response.raise_for_status()
        data = country_response.json()
        return data.get("country") or data.get("country_name") or "Unknown"
    except (requests.RequestException, ValueError):
        return "Unknown"


def build_preview_document(url: str, page_html: str) -> str:
    soup = BeautifulSoup(page_html, "html.parser")

    for tag in soup(["script", "style", "svg", "img", "video", "audio", "iframe", "canvas", "object", "embed", "source", "link", "meta", "noscript"]):
        tag.decompose()

    for anchor in soup.find_all("a", href=True):
        anchor["href"] = urljoin(url, anchor["href"])

    for tag in soup.find_all(["table", "tr", "td", "th", "thead", "tbody"]):
        tag.attrs = {}

    body = soup.body or soup
    body_content = str(body)
    body_content = re.sub(r"<body[^>]*>", "", body_content, count=1, flags=re.IGNORECASE)
    body_content = re.sub(r"</body>", "", body_content, count=1, flags=re.IGNORECASE)
    body_content = body_content.replace("\x00", "")

    if len(body_content) > 140000:
        body_content = body_content[:140000] + "\n\n[preview truncated]"

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><base href='"
        + url
        + "'><style>body{font-family:Arial,sans-serif;max-width:100%;overflow-wrap:anywhere;line-height:1.5;}h1,h2,h3{margin-bottom:0.4em;}p{margin:0.5em 0;}a{color:#2563eb;}ul,ol{padding-left:1.2em;}</style></head><body>"
        + body_content
        + "</body></html>"
    )


with st.form("preview_form"):
    url_input = st.text_input(
        "Enter a URL",
        placeholder="example.com or https://example.com",
        help="The page will be fetched from the server running this app.",
    )
    submitted = st.form_submit_button("Load Preview")

server_country = get_server_country()
st.caption(f"Server country: {server_country}")

if submitted:
    try:
        normalized_url = normalize_url(url_input)
        page_response = fetch_page_from_server(normalized_url)
        page_html = page_response.text
        title_match = re.search(r"<title>(.*?)</title>", page_html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else normalized_url

        st.success(f"Preview loaded from server: {normalized_url}")

        with st.container():
            st.subheader("Preview Pane")
            st.markdown(f"**Page title:** {title}")
            st.markdown(f"**Fetched from:** {normalized_url}")
            try:
                preview_document = build_preview_document(normalized_url, page_html)
                components.html(preview_document, height=760, scrolling=True)
            except Exception:
                st.info("The page was fetched successfully, but the inline preview could not be embedded. Falling back to a lightweight text snapshot.")
                st.text_area("Fetched page preview", page_html[:12000], height=260)
                st.markdown(f"[Open the page in a new tab]({normalized_url})")
    except ValueError as exc:
        st.error(str(exc))
    except requests.RequestException as exc:
        st.error(f"The page could not be loaded from the server: {exc}")
else:
    st.info("Submit a URL to fetch and preview it from the server environment.")
