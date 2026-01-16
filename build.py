import os
import shutil
import subprocess

def install_dependencies(target_dir):
    print(f"Installing dependencies to {target_dir}...")
    # Install directly to the function folder
    subprocess.check_call(["pip", "install", "-r", "requirements.txt", "--target", target_dir])

def create_function_dir(output_dir, source_dirs, source_files):
    print(f"Creating function directory at {output_dir}...")
    
    # 1. Create function dir if not exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 2. Add Source Dirs (e.g. app/) to the function dir
    for s_dir in source_dirs:
        if os.path.exists(s_dir):
            dest_dir = os.path.join(output_dir, os.path.basename(s_dir))
            if os.path.exists(dest_dir):
                shutil.rmtree(dest_dir)
            shutil.copytree(s_dir, dest_dir)

    # 3. Add Source Files (e.g. wms_handler.py)
    for s_file in source_files:
        if os.path.exists(s_file):
            # Rename to main.py if it's the handler, or keep name
            # Here we enforce naming the key handler as 'main.py' if it's wms_handler
            filename = os.path.basename(s_file)
            if "wms_handler" in filename:
                dest_name = "main.py"
            else:
                dest_name = filename
            
            shutil.copy2(s_file, os.path.join(output_dir, dest_name))

if __name__ == "__main__":
    DIST_DIR = "netlify_deploy"
    FUNCTION_NAME = "wms_handler"
    FUNCTION_DIR = os.path.join(DIST_DIR, FUNCTION_NAME)
    
    # 1. Clean Dist Dir
    if os.path.exists(DIST_DIR): shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR)

    # 2. Create Function Folder & Copy Code
    create_function_dir(
        FUNCTION_DIR, 
        source_dirs=["app"], 
        source_files=["netlify/functions/wms_handler.py"]
    )
    
    # 3. Install Deps directly into Function Folder (Vendor)
    install_dependencies(FUNCTION_DIR)
    
    # 4. Create dummy hello for diagnostics
    hello_dir = os.path.join(DIST_DIR, "hello")
    os.makedirs(hello_dir)
    shutil.copy2("netlify/functions/hello.py", os.path.join(hello_dir, "main.py"))

    print("Build Complete.")
