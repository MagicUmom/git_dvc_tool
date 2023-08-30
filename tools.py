###  ------------------------------------------------------------------------------------------- ###
#
#   Steps:
#   1. 建立一個乾淨的 github repo
#   2. 建立一個乾淨的 minio bucket for dvc 的儲存空間
#   3. 到 .env 裡面設定 git 的環境變數如: GIT_REMOTE_ADDRESS, GIT_LOCAL_REPO_ADDRESS
#   4. 如果是第一次初始化，使用以下程式碼, 初始化會在資料夾下新增 .git, .dvc, 以及設定遠端資訊 git remote, dvc remote
#      如果環境下已經有 .git , .dvc 則要先手動刪除
#   version_control_tools(env_path= $$.env的位置$$, verbose = True)    
#   vct.first_init()
#   以上就初始化完成了
#   
#   5. 如果是已經初始化過, 則可以使用
#   version_control_tools(env_path= $$.env的位置$$, verbose = True)    
#   vct.new_add_and_commit(files, commit_msg_header, commit_msg_body)
#   
#   以上 files 是list型態, 裡面放的是這次版本新增或更改的資料名稱,
#   commit_msg_header 是希望是輸入日期(str) yyyymmdd
#   commit_msg_body (str) 可留空, 預測會將這次新增的 files 名稱寫到 commit body內
#
###  ------------------------------------------------------------------------------------------- ###



import git
import subprocess
import os
from dotenv import load_dotenv
import argparse

class version_control_tools(object):
    def __init__(self, env_path="./.env", verbose=False):

        self.verbose = verbose
        load_dotenv(env_path)

        self.CONFIG = {
            "GIT_REMOTE_ADDRESS" : os.getenv("GIT_REMOTE_ADDRESS"),
            "GIT_LOCAL_REPO_ADDRESS" : os.getenv("GIT_LOCAL_REPO_ADDRESS"),

            "MINIO_ROOT_USER" : os.getenv('MINIO_ROOT_USER'),
            "MINIO_ROOT_PASSWORD" : os.getenv('MINIO_ROOT_PASSWORD'),
            "MLFLOW_BUCKET_NAME" : os.getenv('MLFLOW_BUCKET_NAME'),
            "MLFLOW_S3_ENDPOINT_URL" : os.getenv('MLFLOW_S3_ENDPOINT_URL'),
            "MINIO_BUCKET_NAME_FOR_DVC" : os.getenv('MINIO_BUCKET_NAME_FOR_DVC'),
        }   

        if os.path.exists(os.path.join(self.CONFIG["GIT_LOCAL_REPO_ADDRESS"], ".git")):
            self.GIT_REPO = git.Repo(self.CONFIG["GIT_LOCAL_REPO_ADDRESS"])
        else:
            self.print_verbose_msg("git 尚未初始化, 請初始化 git 環境")

    def first_init(self):
        self.git_first_init()
        self.dvc_first_init()

    def git_first_init(self):
        if os.path.exists(os.path.join(self.CONFIG["GIT_LOCAL_REPO_ADDRESS"], ".git")):
            print("[ERROR] 已存在 git 環境, 請清空後再執行初始化設定")
            exit(1)
        repo = git.Repo.init(self.CONFIG['GIT_LOCAL_REPO_ADDRESS'], initial_branch='main')
        repo.create_remote("origin", url=self.CONFIG["GIT_REMOTE_ADDRESS"])
        self.print_verbose_msg("git 環境初始化完成")

    def new_add_and_commit(self, files, commit_msg_header, commit_msg_body):
        self.dvc_add(files)
        self.git_add(files)

        if commit_msg_body == None:
            commit_msg_body = "add files: \n"
            for file in files:
                commit_msg_body += file 
                commit_msg_body += "\n"

        self.git_commit(commit_msg_header, commit_msg_body)
        self.git_push()
        self.dvc_push()

    def dvc_add(self, files):
        def dvc_add_file(file):
            result = subprocess.run(["dvc","add",file], stdout=subprocess.PIPE)
            self.print_verbose_msg(result.stdout.decode("utf-8"))
            print("dvc add {} 完成".format(file))

        for file in files:
            print(file)
            dvc_add_file(file)

    def dvc_first_init(self):
        if os.path.isfile(os.path.join(self.CONFIG["GIT_LOCAL_REPO_ADDRESS"], ".dvc")):
            print("[ERROR] 已存在 dvc 環境, 請清空後再執行初始化設定")
            exit(1)
        
        self.print_verbose_msg("初始化 dvc 環境...")

        # dvc init
        result = subprocess.run(["dvc","init"], stdout=subprocess.PIPE)
        self.print_verbose_msg(result.stdout.decode("utf-8"))

        # dvc remote add -d minio "s3:dvc -f"
        result = subprocess.run(["dvc","remote","add","-d","minio","s3://{}".format(self.CONFIG["MINIO_BUCKET_NAME_FOR_DVC"]),"-f"], stdout=subprocess.PIPE)
        self.print_verbose_msg(result.stdout.decode("utf-8"))

        # dvc remote modify minio endpointurl http://172.16.110.13:9000
        result = subprocess.run(["dvc","remote","modify","minio","endpointurl", self.CONFIG['MLFLOW_S3_ENDPOINT_URL']], stdout=subprocess.PIPE)
        self.print_verbose_msg(result.stdout.decode("utf-8"))

        # dvc remote modify minio access_key_id admin
        result = subprocess.run(["dvc","remote","modify","minio", "access_key_id", self.CONFIG['MINIO_ROOT_USER']], stdout=subprocess.PIPE)
        self.print_verbose_msg(result.stdout.decode("utf-8"))

        # dvc remote modify minio secret_access_key adminsecretkey
        result = subprocess.run(["dvc","remote","modify","minio", "secret_access_key", self.CONFIG['MINIO_ROOT_PASSWORD']], stdout=subprocess.PIPE)
        self.print_verbose_msg(result.stdout.decode("utf-8"))

        self.print_verbose_msg("初始化 dvc 環境完成")

    def git_add(self, files):
        def git_add_files(file):
            filename = file + ".dvc"
            self.GIT_REPO.git.add(filename)
            print("git add {} 完成".format(filename))

        for file in files:
            git_add_files(file)

    def git_commit(self, commit_msg_header, commit_msg_body):
        commit_msg = "TYPE: Weekly Add Data : {} \n{}".format(commit_msg_header,commit_msg_body)
        self.GIT_REPO.git.commit("-m", commit_msg)
        print("git commit 完成")
    
    def git_push(self):
        self.GIT_REPO.git.push("origin", '-u', "main")
        print("git push 完成")

    def dvc_push(self):
        # dvc push
        print("dvc pushing ...")

        result = subprocess.run(["dvc","push"], stdout=subprocess.PIPE)
        self.print_verbose_msg(result.stdout.decode("utf-8"))

        print("dvc push 完成")

    def print_verbose_msg(self, msg):
        if self.verbose:
            print(msg)
        else:
            return 

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', type=str, default='./.env', help='.env path')
    parser.add_argument('--verbose', type=int, default=1, help='0 不顯示詳細資訊, 1顯示詳細資訊')
    parser.add_argument('--files', nargs='+', type=str, default='', help='要讓 dvc 追蹤的檔案名稱')
    parser.add_argument('--msg_header', type=str, default='', help='git commit msg 的 header')
    parser.add_argument('--msg_body', type=str, default='', help='git commit msg 的 body')


    opt = parser.parse_args()
    if opt.files =='':
        files = ["test.txt"]
    else:
        files = opt.files.split(" ")
    if opt.msg_header =='':
        commit_msg_header ="1105"
    if opt.msg_body =='':
        commit_msg_body = "add files: \n"
        for file in files:
            commit_msg_body += file 
            commit_msg_body += "\n"
                      
    vct = version_control_tools(env_path= opt.env, verbose = opt.verbose)
    # vct.first_init()
    vct.new_add_and_commit(files, commit_msg_header, commit_msg_body)
    

if __name__ == "__main__":
    main()