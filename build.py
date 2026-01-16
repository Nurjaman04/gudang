import os
import shutil
import subprocess
import zipfile

def install_dependencies(target_dir):
    print("Installing dependencies...")
    subprocess.check_call(["pip", "install", "-r", "requirements.txt", "-t", target_dir])

def zip_function(output_filename, source_dirs, source_files, deps_dir):
    print(f"Zipping to {output_filename}...")
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add Dependencies
        if os.path.exists(deps_dir):
            for root, dirs, files in os.walk(deps_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, deps_dir)
                    zf.write(file_path, arcname)
        
        # Add Source Dirs (e.g. app/)
        for s_dir in source_dirs:
            if os.path.exists(s_dir):
                for root, dirs, files in os.walk(s_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Keep folder structure (e.g. app/config.py)
                        arcname = os.path.relpath(file_path, os.getcwd()) 
                        zf.write(file_path, arcname)

        # Add Source Files (e.g. wms_handler.py)
        for s_file in source_files:
            if os.path.exists(s_file):
                # Put handler at root of zip (rename if path has subdirs, but here assumes local path)
                # But wait, wms_handler is currently in netlify/functions. 
                # We want it at root of zip.
                arcname = os.path.basename(s_file)
                zf.write(s_file, arcname)

if __name__ == "__main__":
    BUILD_DIR = "build_artifacts"
    DIST_DIR = "netlify_deploy" # New functions dir
    
    # 1. Prepare Dirs
    if os.path.exists(BUILD_DIR): shutil.rmtree(BUILD_DIR)
    if os.path.exists(DIST_DIR): shutil.rmtree(DIST_DIR)
    os.makedirs(BUILD_DIR)
    os.makedirs(DIST_DIR)

    # 2. Install Deps to Build Dir
    install_dependencies(BUILD_DIR)

    # 3. Create Zip for wms_handler
    # We need to grab the handler from netlify/functions/wms_handler.py
    # And package it with 'app' directory.
    zip_function(
        os.path.join(DIST_DIR, "wms_handler.zip"), 
        source_dirs=["app"], 
        source_files=["netlify/functions/wms_handler.py"], 
        deps_dir=BUILD_DIR
    )
    
    # 4. Create Zip for hello (optional, for debug)
    # Reuse dependencies? Hello doesn't need deps, but for consistency lets minimize.
    # Actually simple zip for hello.
    with zipfile.ZipFile(os.path.join(DIST_DIR, "hello.zip"), 'w') as zf:
        zf.write("netlify/functions/hello.py", "hello.py")

    print("Build Complete.")
