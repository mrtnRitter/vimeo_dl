# ------------- IMPORTS -------------
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
import time
import re
import math
import os
import shutil

# ------------- GLOBALS -------------
app_name = "vimeo_dl"
app_description = "Downloads all vimeo videos from account"
app_version = "0.1"
app_author = "https://github.com/mrtnRitter"

driver = None
base_url = "https://vimeo.com/search/library?page={page}&type=video&sort=date_desc"
user_data_dir = r"C:\Users\Avid_Berlin_3\AppData\Local\Temp"
profile_dir = "scoped_dir999_000"
discover_timeout = 30   
total_vids = None
last_page = None
vids_fetched = None
vids_txt_filename = "vids.txt"
download_dir = r"E:\tmp Martin\Download Vimeo\dl"
debug = False


# ------------- FUNCTIONS -------------

def setup_driver(headless, download):
    """
    Setup the Chrome driver with options.
    """
    global driver
    options = Options()

    if debug:
        headless = False
        options.add_experimental_option("detach", True)
    else:
        headless = headless
    
    if headless:
        options.add_argument("--headless")
    
    options.add_argument("--log-level=1")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--window-size=1500,1400")
    
    if user_data_dir and profile_dir and not download:
        options.add_argument(f"user-data-dir={user_data_dir}")
        options.add_argument(f"profile-directory={profile_dir}")

    if download:
        download = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", download)

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(discover_timeout)



def get_total_vids_and_last_page():
    """
    Get the last page number from the total videos.
    """
    try:
        page = 0
        target_url = base_url.format(page=page)
        driver.get(target_url)
        time.sleep(5)
        total_vids_raw = driver.find_element(By.CSS_SELECTOR, ".chakra-text.css-ygycye").text   
        match = re.search(r"([\d,]+)", total_vids_raw)
        if match:
            total_vids = int(match.group(1).replace(",", ""))
        
        last_page = math.ceil(total_vids/24)
        return total_vids, last_page

    except NoSuchElementException:
        print("[ERROR] Unable to find total video count.")
        exit(1)



def close_modal_dl_dialog():
    """
    Close the modal dialog about processing downloads.
    """
    js_is_moddia = "return document.querySelectorAll('button.chakra-button.css-1yk6z2g').length > 0;"
    if driver.execute_script(js_is_moddia):
        js_click_ok = "document.querySelector('button.chakra-button.css-1yk6z2g').click();"
        driver.execute_script(js_click_ok)
        return True
    
    return False



def fetch_vid_data(delete=False):
    """
    Get all videos from the current page.
    """
    global driver
    global vids_fetched
    global total_vids
    global discover_timeout
    
    try:
        list = driver.find_elements(By.CLASS_NAME, "css-ebczr7")
        for i, item in enumerate(list):
            vid_name = item.find_element(By.CSS_SELECTOR, ".chakra-text.css-qsz7k4").text
            vid_date = item.find_element(By.CSS_SELECTOR, ".chakra-text.css-806m9j").text
            vid_folder = item.find_element(By.CSS_SELECTOR, ".chakra-text.css-bvdmf7").text
            
            three_dot_menu = item.find_element(By.CSS_SELECTOR, ".chakra-stack.css-1fkbjl")
            three_dot_menu.click()
            time.sleep(1)

            all_three_dot_containers = driver.find_elements(By.CLASS_NAME, "css-h9umap")
            for three_dot_container in all_three_dot_containers:
                if three_dot_container.is_displayed():
                    three_dot_options = three_dot_container.find_elements(By.TAG_NAME, "Button")
                    for three_dot_option in three_dot_options:
                        
                        # Download video
                        if three_dot_option.get_attribute("data-index") == "2":
                            three_dot_option.click()
                            time.sleep(1)

                            if not close_modal_dl_dialog():
                                dl_opts = driver.find_elements(By.CLASS_NAME, "css-1lekzkb")
                                for dl_opt in dl_opts:
                                    if dl_opt.find_element(By.CSS_SELECTOR, ".chakra-text.css-qo6t4t").text == "Original":
                                        dl_link_org = dl_opt.find_element(By.TAG_NAME, "a").get_attribute("href")
                                        break
                                
                                # Close the download options modal
                                driver.find_element(By.CSS_SELECTOR, ".chakra-modal__close-btn.css-93kv31").click()

                                # Scroll a bit down
                                vid_container = driver.find_element(By.CLASS_NAME, "css-yt9y4i")
                                driver.execute_script("arguments[0].scrollBy(0, 75);", vid_container)
                            
                            else:
                                dl_link_org = "Dead video"


                        # Delete video
                        if delete:
                            pass
                            # if three_dot_option.get_attribute("data-index") == "5":
                            #     delete_vid = three_dot_option
                            #     #delete_vid.click()

            with open(vids_txt_filename, "a", encoding="utf-8") as f:
                vids_fetched += 1
                line = f"{vids_fetched}\t{vid_date}\t{vid_folder}\t{vid_name}\t{dl_link_org}\n"
                f.write(line)
                print(vids_fetched, vid_name)
                

                
        return True

    except NoSuchElementException:
            return False



def get_dl_file():
    dl_name = None
    time.sleep(1)

    while not dl_name:
        dl_name = os.listdir(download_dir)

        for fname in os.listdir(download_dir):
            if fname.endswith(".crdownload"):
                dl_name = fname
                break

    crdownload_path = os.path.join(download_dir, dl_name)
    file_path = crdownload_path.replace(".crdownload", "")

    if os.path.exists(file_path) and not os.path.exists(crdownload_path):
        dl_file = os.path.basename(file_path)
        return dl_file
    
    time.sleep(1)
    

def login():
    """
    Login to the Vimeo account.
    """
    global driver
    browser_open = True
    setup_driver(headless=False, download=False)

    driver.get("https://vimeo.com/login")

    while browser_open:
        try:
            driver.title
            browser_open = True
        except WebDriverException:
            browser_open = False
            driver = None


def fetch():
    """
    Fetch all videos from the Vimeo account.
    """

    global driver
    setup_driver(headless=False, download=False)

    total_vids, last_page = get_total_vids_and_last_page()
    first_page = 1
    last_page = 10

    global vids_fetched
    vids_fetched = (first_page-1)*24

    for page in range(first_page, last_page + 1):
        target_url = base_url.format(page=page)
        driver.get(target_url)
        time.sleep(5)

        if not fetch_vid_data(delete=False):
            driver.refresh()
            if not fetch_vid_data(delete=False):
                print(f"[FATAL] Unable to fetch video data on page {page}")
                exit(1)

    driver.quit()
    driver = None

    if vids_fetched == total_vids:
        print(f"All {vids_fetched} videos done.")
    else:
        print(f"{vids_fetched} videos done, but expected {total_vids}. Something went wrong. Operation aborted.")
        exit(0)



def download():
    """
    Download videos from the Vimeo account.
    """
    global driver
    setup_driver(headless=True, download=True)
    with open(vids_txt_filename, "r", encoding="utf-8") as f:
        for line in f:
            all_vals = line.strip().split("\t")
            if len(all_vals) >= 5:
                vids_fetched, _, vid_folder, vid_name, dl_link_org = all_vals[:5]
                if dl_link_org != "Dead video":
                    driver.get(dl_link_org)
                
                    print(f"Downloading video: {vids_fetched} {vid_name}")
                    download_file = get_dl_file()
                    ext = os.path.splitext(download_file)[1]

                    src_path = os.path.join(download_dir, download_file)
                    dst_folder = os.path.join(download_dir, vid_folder)
                    dst_path = os.path.join(dst_folder, vid_name + ext)

                    if not os.path.exists(dst_folder):
                        os.makedirs(dst_folder)
                    
                    shutil.move(src_path, dst_path)
                    
                    print("Download abgeschlossen!")
                else:
                    print("Dead video - no download")

    driver.quit()
    driver = None


def ask_operation(with_login=True):
    """
    Ask the user for the operation to perform.
    """
    if with_login:
        operation = input("login (l), fetch video data (f), download videos (d), or all (a)? ").strip().lower()
    else:
        operation = input("fetch video data (f), download videos (d), or all (a)? ").strip().lower()
    return operation


# ------------- MAIN -------------

operation = ask_operation(with_login=True)

if operation == "l":
    login()
    operation = ask_operation(with_login=False)

if operation == "f":
    fetch()

elif operation == "d":
    download()

elif operation == "a":
    login()
    fetch()
    download()

else:
    print("Invalid operation. Please choose 'f', 'd', or 'b'.")
    exit(1)