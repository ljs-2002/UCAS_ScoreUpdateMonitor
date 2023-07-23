import requests
import re
import base64
import ddddocr
import json
import os
import sys
from .score_update_logger import MyLogger
from Crypto.Cipher import PKCS1_v1_5 as Cipher_pksc1_v1_5
from Crypto.PublicKey import RSA

logger = MyLogger('ScoreUpdateMonitor')
class ScoreUpdateMonitor:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.82'
    }
    login_url = 'https://sep.ucas.ac.cn/'
    pic_url = 'https://sep.ucas.ac.cn/changePic'
    slogin_url = 'https://sep.ucas.ac.cn/slogin'
    redirect_url = 'https://sep.ucas.ac.cn/portal/site/226/821'
    score_base_url = 'https://jwxk.ucas.ac.cn/score/bks/'
    pub_re = re.compile(r'var jsePubKey = \'(.*?)\'')
    error_re = re.compile(r'<div class="alert alert-error">(.*?)</div>',re.S)
    redirect_re = re.compile(r'2秒钟没有响应请点击<a href="(.*?)"><strong>这里', re.S)
    root_path = os.path.dirname(os.path.realpath(sys.argv[0]))
    userInfo_path = os.path.join(root_path,'config','userInfo.json')
    cur_score_path = os.path.join(root_path,'tmp','cur_score.json')
    module_path = os.path.join(root_path,'module','sep.onnx')
    charsets_path = os.path.join(root_path,'module','charsets.json')
    def __init__(self):
        # 使用自己训练的模型
        self.ocr = ddddocr.DdddOcr(show_ad=False,ocr=False,det=False,import_onnx_path=self.module_path,charsets_path=self.charsets_path)
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.keep_alive = True
        with open(self.userInfo_path,'r') as f:
            userInfo = json.load(f)
        self.username = userInfo['userName']
        self.password = userInfo['password']
        self.apikey = userInfo['apikey']
        self.gpa = 0.0
    
    @staticmethod
    def encrypt(password, public_key):
        public_key = '-----BEGIN PUBLIC KEY-----\n'+ public_key + '\n-----END PUBLIC KEY-----'
        rsakey = RSA.importKey(public_key)
        cipher = Cipher_pksc1_v1_5.new(rsakey)
        cipher_text = base64.b64encode(cipher.encrypt(password.encode()))
        return cipher_text.decode()

    def __do_login(self):
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
                raise Exception(f'get certCode error code: {pic.status_code}, {pic.text}')
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
                raise Exception(f'login error code: {response.status_code}, {response.text}')
        else:
            self.session.close()
            raise Exception(f'try to login but fail, error code: {response.status_code}, {response.text}')
    
    def __login(self,retry=3):
        count = 0
        while True:
            # 若登陆失败的原因是验证码错误，则重试
            try:
                self.__do_login()
                return
            except Exception as e:
                if str(e) == '验证码错误':
                    count += 1
                    if count < retry:
                        continue
                    else:
                        raise Exception('验证码错误次数过多')
                else:
                    raise e
    def __cal_GPA(self,all_score_date:list[dict]):
        gpa_table = {90: 4.0, 89: 3.9, 88: 3.9, 87: 3.9, 86: 3.8,
                    85: 3.8, 84: 3.7, 83: 3.7, 82: 3.6, 81: 3.5,
                    80: 3.5, 79: 3.4, 78: 3.4, 77: 3.3, 76: 3.3,
                    75: 3.2, 74: 3.1, 73: 3.0, 72: 2.9, 71: 2.8,
                    70: 2.7, 69: 2.7, 68: 2.6, 67: 2.5, 66: 2.4,
                    65: 2.3, 64: 2.3, 63: 2.2, 62: 2.1, 61: 1.8,
                    60: 1.6, 59: 0.0
                }
        total_credit = 0
        total_gpa = 0
        for class_ in all_score_date:
            score = class_['score']
            if score.isdigit() is False:
                continue
            score = int(score)
            if score > 90:
                score = 90
            elif score < 60:
                score = 59
            total_gpa += gpa_table[score]*class_['courseCredit']
            total_credit += class_['courseCredit']
        gpa = total_gpa / total_credit
        return gpa
            
        
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
                self.gpa = self.__cal_GPA(score_data['list'])
                url = self.score_base_url + cur_term + '.json'
                # 获取当前学期的成绩
                response = self.session.get(url)
                self.session.close()
                if response.status_code == 200:
                    cur_score_data = response.json()
                    cur_score_data['termId'] = cur_term
                    return cur_score_data
                else:
                    raise Exception(f'get current score error code: {response.status_code}, {response.text}')
            else:
                self.session.close()
                raise Exception(f'redirect error code: {response.status_code}, {response.text}')
        else:
            self.session.close()
            raise Exception(f'get redirect url error code: {response.status_code}, {response.text}')
    
    def __compare_score(self, cur_score_data):
        gpa_info = f"GPA/实时GPA: {cur_score_data['student']['gpaInland']}/{self.gpa}\n\n排名: {cur_score_data['student']['gpaInlandSort']}/{cur_score_data['gpasorttotal']}\n\n"
        if not os.path.exists(self.cur_score_path):
            with open(self.cur_score_path, 'w',encoding='utf-8') as f:
                json.dump(cur_score_data, f, ensure_ascii=False)
            return cur_score_data['list'],gpa_info,True
        with open(self.cur_score_path, 'r',encoding='utf-8') as f:
            last_score_data = json.load(f)
        cur_score = cur_score_data['list']
        last_score = last_score_data['list']
        cur_id = cur_score_data['termId']
        last_id = last_score_data['termId']
        send_message = False
        # 如果不同学期或有新科目出分，或GPA变化，或GPA排名变化，则更新缓存文件
        if cur_id != last_id or len(cur_score) != len(last_score) or cur_score_data['student']['gpaInland'] != last_score_data['student']['gpaInland'] or cur_score_data['student']['gpaInlandSort'] != last_score_data['student']['gpaInlandSort']:
            with open(self.cur_score_path, 'w',encoding='utf-8') as f:
                json.dump(cur_score_data, f, ensure_ascii=False)
            send_message = True
        return [item for item in cur_score if item not in last_score],gpa_info,send_message

    def __send_api_message(self,error:bool,diff_list:list[dict]=[],error_message:str=None,gpa_info:str=None):
        api_url = f'https://sctapi.ftqq.com/{self.apikey}.send?'
        title = 'Score Update Monitor: '
        if error:
            title = title + 'Error'
            content = error_message
        elif len(diff_list) > 0:
            title = title + 'Score Update'
            content = gpa_info+'|更新的科目|学分|成绩|\n|--|--|--|\n'
            for item in diff_list:
                line = f'|{item["courseName"]}|{item["courseCredit"]}|{item["score"]}|\n'
                content = content + line
        else:
            title = title + 'GPA Update'
            content = gpa_info
        postdata = {
            'title': title,
            'desp': content
        }
        if gpa_info is not None:
            postdata['short'] = gpa_info
        logger.log(f'send message: {content}')
        if len(self.apikey)>0:
            logger.log('send message to api')
            response = requests.post(api_url, data=postdata)
            if response.status_code != 200:
                raise Exception(f'send message error code: {response.status_code}, {response.text}')
        else:
            logger.log('apikey is empty, do not send message to api')
        


    def launch(self):
        logger.log('---------------')
        logger.log('start')
        try:
            self.__login()
            cur_score_data = self.__get_score()
            diff_list,gpa_info,send_message = self.__compare_score(cur_score_data)
        except Exception as e:
            logger.log(f'error: {e}')
            try:
                self.__send_api_message(True,error_message=str(e))
            except Exception as e:
                logger.log(f'send message error: {e}')
        else:
            try:
                if send_message:
                    self.__send_api_message(False,diff_list=diff_list,gpa_info=gpa_info)
                else:
                    logger.log('there is no update')
            except Exception as e:
                logger.log(f'send message error: {e}')
        logger.log('finish')
        logger.log('---------------')