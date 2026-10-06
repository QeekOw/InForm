import os
import sys
import time
import requests
from kaggle.api.kaggle_api_extended import KaggleApi, ApiListKernelSessionOutputRequest

CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB chunks

def download_file_with_resume(url: str, dest_path: str, max_retries: int = 10):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    for attempt in range(max_retries):
        existing_size = os.path.getsize(dest_path) if os.path.exists(dest_path) else 0
        headers = {}
        if existing_size > 0:
            headers['Range'] = f'bytes={existing_size}-'
            
        try:
            r = requests.get(url, headers=headers, stream=True, timeout=30)
            
            # If server doesn't support range or file is already complete
            if r.status_code == 416:  # Range Not Satisfiable -> file already complete!
                print(f"File {os.path.basename(dest_path)} is already complete ({existing_size} bytes).", flush=True)
                return True
                
            if r.status_code not in (200, 206):
                print(f"HTTP {r.status_code} on attempt {attempt+1}, retrying in 3s...", flush=True)
                time.sleep(3)
                continue
                
            total_size = None
            if r.status_code == 206:
                content_range = r.headers.get('Content-Range') # e.g. bytes 100-200/500
                if content_range and '/' in content_range:
                    total_size = int(content_range.split('/')[-1])
                mode = 'ab'
            else:
                total_length = r.headers.get('Content-Length')
                if total_length:
                    total_size = int(total_length)
                mode = 'wb'
                existing_size = 0
                
            downloaded = existing_size
            last_print = time.time()
            
            with open(dest_path, mode) as f:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.time()
                        if now - last_print > 2.0 or (total_size and downloaded >= total_size):
                            last_print = now
                            if total_size:
                                pct = (downloaded / total_size) * 100
                                mb_down = downloaded / (1024 * 1024)
                                mb_tot = total_size / (1024 * 1024)
                                print(f"[{os.path.basename(dest_path)}] {mb_down:.1f}MB / {mb_tot:.1f}MB ({pct:.1f}%)", flush=True)
                            else:
                                mb_down = downloaded / (1024 * 1024)
                                print(f"[{os.path.basename(dest_path)}] {mb_down:.1f}MB downloaded", flush=True)
                                
            if total_size and downloaded < total_size:
                print(f"Downloaded {downloaded} of {total_size} bytes, retrying resume...", flush=True)
                time.sleep(2)
                continue
                
            print(f"Successfully downloaded {os.path.basename(dest_path)} ({downloaded} bytes).", flush=True)
            return True
            
        except (requests.RequestException, ConnectionError) as e:
            print(f"Connection error on attempt {attempt+1}: {e}. Retrying in 5s...", flush=True)
            time.sleep(5)
            
    print(f"Failed to download {dest_path} after {max_retries} attempts.", flush=True)
    return False

def main():
    target_dir = os.path.abspath("models/donut-270-v9")
    os.makedirs(target_dir, exist_ok=True)
    
    print(f"Target directory: {target_dir}", flush=True)
    print("Authenticating with Kaggle...", flush=True)
    api = KaggleApi()
    api.authenticate()
    
    print("Fetching file list for qeekowen/module-1-donut-270-v9-training...", flush=True)
    with api.build_kaggle_client() as kaggle_client:
        req = ApiListKernelSessionOutputRequest()
        req.user_name = "qeekowen"
        req.kernel_slug = "module-1-donut-270-v9-training"
        req.page_size = 100
        res = kaggle_client.kernels.kernels_api_client.list_kernel_session_output(req)
        
    needed_files = [
        "donut-270-v9/config.json",
        "donut-270-v9/generation_config.json",
        "donut-270-v9/model.safetensors",
        "donut-270-v9/processor_config.json",
        "donut-270-v9/tokenizer.json",
        "donut-270-v9/tokenizer_config.json",
    ]
    
    files_to_download = [f for f in (res.files or []) if f.file_name in needed_files]
    print(f"Found {len(files_to_download)} matching files to download.", flush=True)
    
    for item in files_to_download:
        filename = os.path.basename(item.file_name)
        dest_path = os.path.join(target_dir, filename)
        print(f"\n--- Downloading {filename} ---", flush=True)
        success = download_file_with_resume(item.url, dest_path)
        if not success:
            sys.exit(1)
            
    print("\nALL FILES DOWNLOADED SUCCESSFULLY!", flush=True)

if __name__ == "__main__":
    main()
