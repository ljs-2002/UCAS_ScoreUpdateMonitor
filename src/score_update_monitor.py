# step1: 访问登陆页面，获取cookie：JSESSIONID
import requests
import re
import base64
import ddddocr
import json
import os.path
from os import getcwd
from Crypto.Cipher import PKCS1_v1_5 as Cipher_pksc1_v1_5
from Crypto.PublicKey import RSA


class ScoreUpdateMonitor:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.82'
    }
    login_url = 'https://sep.ucas.ac.cn/'
    pic_url = 'https://sep.ucas.ac.cn/changePic'
    slogin_url = 'https://sep.ucas.ac.cn/slogin'
    redirect_url = 'https://sep.ucas.ac.cn/portal/site/226/821'
    score_base_url = 'https://jwxk.ucas.ac.cn/score/bks/'
    userInfo_path = os.path.join(getcwd(),'config','userInfo.json')
    cur_score_path = os.path.join(getcwd(),'tmp','cur_score.json')
    ocr = ddddocr.DdddOcr()
    pub_re = re.compile(r'var jsePubKey = \'(.*?)\'')
    error_re = re.compile(r'<div class="alert alert-error">(.*?)</div>',re.S)
    redirect_re = re.compile(r'2秒钟没有响应请点击<a href="(.*?)"><strong>这里', re.S)
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.keep_alive = True
        with open(self.userInfo_path,'r') as f:
            userInfo = json.load(f)
        self.username = userInfo['userName']
        self.password = userInfo['password']
        self.apikey = userInfo['apikey']
    
    @staticmethod
    def encrypt(password, public_key):
        public_key = '-----BEGIN PUBLIC KEY-----\n'+ public_key + '\n-----END PUBLIC KEY-----'
        rsakey = RSA.importKey(public_key)
        cipher = Cipher_pksc1_v1_5.new(rsakey)
        cipher_text = base64.b64encode(cipher.encrypt(password.encode()))
        return cipher_text.decode()

    def __login(self):
        response = self.session.get(self.login_url)
        if response.status_code == 200:
            # 获取公钥
            pub_key = self.pub_re.findall(response.text)[0]
            # 获取验证码
            pic = self.session.get(self.pic_url)
            # 识别验证码
            if pic.status_code == 200:
                img_bytes = pic.content
                certCode = self.ocr.classification(img_bytes)
            else:
                self.session.close()
                raise Exception(f'get certCode error code: {pic.status_code}')
            # 密码的加密
            password = self.encrypt(self.password, pub_key)
            # 登陆
            data = {
                'userName': self.username,
                'pwd': password,
                'certCode': certCode,
                'sb': 'sb'
            }
            response = self.session.post(self.slogin_url, data=data)
            if response.status_code == 200:
                fail = self.error_re.findall(response.text)
                if len(fail) != 0:
                    self.session.close()
                    raise Exception(fail[0])
            else:
                self.session.close()
                raise Exception(f'login error code: {response.status_code}')
        else:
            self.session.close()
            raise Exception(f'try to login but fail, error code: {response.status_code}')
        
    def __get_score(self):
        response = self.session.get(self.redirect_url)
        if response.status_code == 200:
            redirect_url = self.redirect_re.findall(response.text)[0]
            response = self.session.get(redirect_url)
            if response.status_code == 200:
                # 从所有成绩界面中获取当前学期的ID
                all_url = self.score_base_url + 'all.json'
                response = self.session.get(all_url)
                score_data = response.json()
                cur_term = str(score_data['openRetestTerm']['termId'])
                url = self.score_base_url + cur_term + '.json'
                # 获取当前学期的成绩
                response = self.session.get(url)
                self.session.close()
                if response.status_code == 200:
                    cur_score_data = response.json()
                    cur_score_data['termId'] = cur_term
                    return cur_score_data
                else:
                    raise Exception(f'get current score error code: {response.status_code}')
            else:
                self.session.close()
                raise Exception(f'redirect error code: {response.status_code}')
        else:
            self.session.close()
            raise Exception(f'get redirect url error code: {response.status_code}')
    
    def __compare_score(self, cur_score_data):
        gpa_info = f"GPA: {cur_score_data['student']['gpaInland']}, 排名: {cur_score_data['student']['gpaInlandSort']}/{cur_score_data['gpasorttotal']}\n\n"
        if not os.path.exists(self.cur_score_path):
            with open(self.cur_score_path, 'w',encoding='utf-8') as f:
                json.dump(cur_score_data, f, ensure_ascii=False)
            return cur_score_data['list'],gpa_info
        with open(self.cur_score_path, 'r',encoding='utf-8') as f:
            last_score_data = json.load(f)
        cur_score = cur_score_data['list']
        last_score = last_score_data['list']
        cur_id = cur_score_data['termId']
        last_id = last_score_data['termId']
        if cur_id != last_id or len(cur_score) != len(last_score):
            with open(self.cur_score_path, 'w',encoding='utf-8') as f:
                json.dump(cur_score_data, f, ensure_ascii=False)
        return [item for item in cur_score if item not in last_score],gpa_info

    def __send_api_message(self,error:bool,diff_list:list[dict]=[],error_message:str=None,gpa_info:str=None):
        api_url = f'https://sctapi.ftqq.com/{self.apikey}.send?'
        title = 'Score Update Monitor'
        if error:
            title = title + ' Error'
            content = error_message
        else:
            title = title + ' Update'
            content = gpa_info+'|更新的科目|学分|成绩|\n|--|--|--|\n'
            for item in diff_list:
                line = f'|{item["courseName"]}|{item["courseCredit"]}|{item["score"]}|\n'
                content = content + line
        postdata = {
            'title': title,
            'desp': content
        }
        if gpa_info is not None:
            postdata['short'] = gpa_info
        response = requests.post(api_url, data=postdata)
        if response.status_code != 200:
            raise Exception(f'send message error code: {response.status_code}')
        


    def launch(self):
        try:
            self.__login()
            cur_score_data = self.__get_score()
        except Exception as e:
            self.__send_api_message(True,error_message=str(e))
            raise e
        else:
            diff_list,gpa_info = self.__compare_score(cur_score_data)
            if len(diff_list) != 0:
                self.__send_api_message(False,diff_list=diff_list,gpa_info=gpa_info)
        print('done')