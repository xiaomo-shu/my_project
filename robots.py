#! -*- coding:utf-8 -*-
import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
from config.config import *
from slider import douyin_slid
from tools import common
from tools.deal_picture import compress_image
from tools import robots_utils
import signal
import json
import sys


class robot:

    def __init__(self):
        self.url = 'https://sso.douyin.com/login/?service=https%3A%2F%2Frenzheng.douyin.com%2Fguide%3Ffiji_source%3Ddouyin'
        self.send_login_verifica_code_time = None
        self.send_auth_verifica_code_time = int(round(time.time() * 1000))
        self.driver = None
        self._init_err_code()

    def clear_resource(self, signum=15, e=0):
        """
        处理信号的函数
        """
        print('will quit webdriver and kill myself')
        print('receive signal: %d at %s' % (signum, str(time.ctime(time.time()))))
        self.driver.quit()
        sys.exit()

    def openDriver(self):
        chrome_options = Options()
        # 谷歌文档提到需要加上这个属性来规避bug
        chrome_options.add_argument('--disable-gpu')
        # 浏览器不提供可视化页面. linux下如果系统不支持可视化不加这条会启动失败
        # chrome_options.add_argument('--headless')
        # 以最高权限运行
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=Driver_Path)  # 这样就完成了浏览器对象的初始化
        self.browser_pid = self.driver.service.process.pid

        self.douyin_slider = douyin_slid(driver=self.driver)
        time.sleep(2)
        self.cookies = self.get_cookies()
        # signal.signal(15, self.clear_resource)

    def closeDriver(self):
        if self.driver is None:
            pass
        else:
            self.driver.quit()
            self.driver = None
            self.douyin_slider.reload_driver(None)

    def get_cookies(self):
        cookies = {}
        for i in self.driver.get_cookies():
            cookies[i["name"]] = i["value"]
        return cookies

    def refresh(self):
        #self.driver.get("https://renzheng.douyin.com/payment")
        if self.driver.find_elements_by_xpath("//button[@class='ant-btn register-button']") != []:  # 立即付款按钮
            self.driver.find_element_by_xpath("//button[@class='ant-btn register-button']").click()
        elif self.driver.find_elements_by_xpath("//div[@class='refresh']/i[@class='anticon anticon-reload']") != []:  # 二维码刷新
            self.driver.find_element_by_xpath("//div[@class='refresh']/i[@class='anticon anticon-reload']").click()

    def get_snap(self):  # 对目标网页进行截屏。这里截的是全屏
        self.driver.save_screenshot('full_snap.png')
        page_snap_obj = Image.open('full_snap.png')
        return page_snap_obj

    def get_pay_image(self, phone, cookies):

        if self.driver is None:
            print("driver is None,try add cookie and openDriver")
            self.openDriver()
            self.driver.get(url='https://renzheng.douyin.com/payment')
            self.driver.delete_all_cookies()
            for cookie in cookies:
                if 'expiry' in cookie:
                    del cookie['expiry']
                self.driver.add_cookie(cookie)
            self.driver.get(url='https://renzheng.douyin.com/payment')
            time.sleep(2)
            self.cookies = self.get_cookies()


        status = None
        message = None
        count=1
        while count<6:
            self.refresh()
            print("第{}次获取支付验证码".format(count))
            if self.driver.find_elements_by_xpath("//div[@class='qrcode-wrapper ']/canvas") != []:
                img = self.driver.find_element_by_xpath("//div[@class='qrcode-wrapper ']/canvas")
                time.sleep(2)
                location = img.location
                print(location)
                size = img.size
                left = location['x']
                top = location['y']
                right = left + size['width']
                bottom = top + size['height']

                page_snap_obj = self.get_snap()
                image_obj = page_snap_obj.crop((left, top, right, bottom))
                image_obj.save(os.path.join(PATH, phone, "payment_img.png"))
                status = True
                message = 'success'
                break
            else:
                self.refresh()  # 刷新
                count+=1
                continue
        result = {
            'status': status,
            'message': message,
            'cookies': self.driver.get_cookies()
        }
        return result

    def submit_auth_data(self, phone, auth_verifica_code, cookies):
        self.cookies = self.get_cookies()
        print('submit_auth_data')
        status = None
        status_code = None
        message = None
        total_count=1
        while total_count<6:
            print("第{}次提交认证信息".format(total_count))
            try:
                # 填写验证码
                print("begin 填写验证码")
                yzCode = self.driver.find_element_by_xpath("//input[@id='vercode']")
                yzCode.clear()
                yzCode.send_keys(auth_verifica_code)
                print("finsh 填写验证码")

                # 点击提交资料
                print("begin 点击提交资料")
                self.driver.find_element_by_xpath("//button[@type='submit']").click()
                time.sleep(5)
                print("finsh 点击提交资料")

                # 判断是否提交成功
                exit_flag = 0
                if self.driver.find_elements_by_xpath("//button[@type='submit']") == []:
                    status = True
                    message = '提交资料成功'
                    status_code = 200
                    break
                else:
                    # 这里可能是验证码过期，也可能是其他异常情况
                    status = False
                    is_break = False
                    if self.driver.find_elements_by_xpath("//div[@class='ant-form-explain']"):
                        error_msg = self.driver.find_element_by_xpath("//div[@class='ant-form-explain']").text
                    else:
                        error_msg = '未知'
                    if '运营手机号超过上限，请更换' in error_msg:
                        status_code = 232
                        is_break = True
                    elif '校验失败' in error_msg:
                        status_code = 233
                        is_break = True
                    elif '验证码验证次数过多' in error_msg:
                        status_code = 234
                        is_break = True
                    else:
                        status_code = 235
                        is_break = False
                    message = self.auth_err_code_dict[status_code] + '抖音提示信息为: {}'.format(error_msg)
                    total_count += 1
                    print("第{}次提交认证信息失败, {}".format(total_count, message))
                    if is_break:
                        break
                    else:
                        continue
            except Exception as e:
                print(e)
                print("第{}  次提交认证信息异常, {}".format(total_count, e))
                status = False
                status_code = 231
                message = self.auth_err_code_dict[status_code]
                total_count += 1
                continue
        cookies = self.driver.get_cookies()
        result = {
            'status': status,
            'status_code': status_code,
            'message': message,
            'cookies': cookies
        }
        print('{} login {}'.format(phone, result))
        return result

    def send_login_verifica_code(self, phone):
        if self.driver is None:
            print('driver is None, start now')
            self.openDriver()
        else:
            self.driver.get(self.url)
        status = None
        status_code = None
        message = None
        count = 1
        while count < 5:
            print("第{}次发送登录验证码".format(count))
            try:
                self.driver.get(self.url)
                time.sleep(2)
                account_type = self.driver.find_element_by_id('login-switch-form')
                account_type.click()
                time.sleep(1)
                # 填写手机号
                phone_number = self.driver.find_element_by_id('user-mobile')
                phone_number.clear()
                phone_number.send_keys(phone)

                # 发送验证码
                code_button = self.driver.find_element_by_xpath("//span[@class='get-code']")
                code_button.click()
                self.send_login_verifica_code_time = int(round(time.time() * 1000))

                time.sleep(3)
                # 弹出验证码框为   style="display: block;"
                # 没弹出为        style="display: none;"
                captcha_element = self.driver.find_element_by_xpath("//div[@id='captcha_container']").get_attribute("style")
                if captcha_element == 'display: block;':
                    # 如果出现滑块
                    print('出现滑块，开始拖动滑动验证码')
                    is_slider_success = self.douyin_slider.slide()  # 拖动滑块验证
                    if is_slider_success:
                        if self.driver.find_element_by_id('login-msg').get_attribute("style") == 'display: block;':
                            login_msg = self.driver.find_element_by_id('login-msg').text
                            if '验证码发送太频繁，请稍后再试' in login_msg:
                                print("验证码发送太频繁,请稍后再试")
                                status_code = 209
                                message = self.login_err_code[status_code] + '抖音提示信息为: {}'.format(login_msg)
                            else:
                                print("登陆失败,提示信息还没见过:  {}".format(login_msg))
                                status_code = 210
                                message = self.login_err_code[status_code] + '抖音提示信息为: {}'.format(login_msg)
                            break
                        else:
                            print("登录发送验证码成功, 绕过滑块验证码")
                            status = True
                            status_code = 200
                            message = 'success'
                            break
                    else:
                        print('绕过滑块验证码失败')
                        status = False
                        status_code = 211
                        message = self.login_err_code[status_code]
                        self.closeDriver()
                        self.openDriver()
                        count += 1
                        continue
                elif self.driver.find_element_by_id('login-msg').get_attribute("style") == 'display: block;':
                    status = False
                    login_msg = self.driver.find_element_by_id('login-msg').text
                    if login_msg == '请使用抖音手机APP登录':
                        status_code = 207
                        message = self.login_err_code[status_code] + '抖音提示信息为: {}'.format(login_msg)
                    elif '验证码发送太频繁，请稍后再试' in login_msg:
                        print("验证码发送太频繁,请稍后再试")
                        status_code = 209
                        message = self.login_err_code[status_code] + '抖音提示信息为: {}'.format(login_msg)
                    else:
                        print("登陆失败,提示信息还没见过:  {}".format(login_msg))
                        status_code = 210
                        message = self.login_err_code[status_code] + '抖音提示信息为: {}'.format(login_msg)
                    break
                elif 's' in self.driver.find_elements_by_xpath("//div[@id='mobile-code-get']/span")[0].text:
                    print("登录发送验证码成功, 无滑块验证码1")
                    status = True
                    status_code = 200
                    message = self.login_err_code[status_code]
                    break
                else:
                    print("登录发送验证码成功, 无滑块验证码2")
                    status = True
                    status_code = 200
                    message = self.login_err_code[status_code]
                    break
            except Exception as e:
                print("{} 登录异常,异常信息为 {}".format(phone, e))
                status = False
                status_code = 203
                message = '发送登录验证码失败,爬虫出现异常'
                self.driver.refresh()
                count += 1
                continue
        result = {
            'status': status,
            'status_code': status_code,
            'message': message,
        }

        return result

    def is_login_success(self, phone):
        print("{},登录成功".format(phone))
        if self._is_possible_auth(phone=phone):
            print('用户社区状态检验通过')
        else:
            status_code = 204  # 用户当前社区状态不能申请企业认证
            message = self.login_err_code[status_code]
            return status_code, message

        if self._is_pay(phone=phone):
            print('用户已提交资料，现等待付款')
            status_code = 205  # 企业认证资料已成功提交，请支付审核服务费。认证审核将会在支付完成后进行
            message = self.login_err_code[status_code]
            return status_code, message
        else:
            print('用户尚未提交资料认证，可继续校验')

        finsh_flag, msg = self._is_finsh(phone=phone)
        if finsh_flag:
            status_code = 206  # 恭喜，您已通过企业认证审核。认证有效期至xxxx年xx月xx日
            message = msg
            return status_code, message
        else:
            print('用户不属于完成支付这个状态，可返回登录成功了')

        status_code = 200  # 登录成功
        message = self.login_err_code[status_code]
        return status_code, message

    # 200 登录成功
    # 201 登录失败, 原因未知
    # 202 登陆失败, 登录验证码错误
    # 203 登录失败, 验证码过期
    # 204 登录成功, 用户当前社区状态不能申请企业认证
    # 205 登录成功, 企业认证资料已成功提交，请支付审核服务费。认证审核将会在支付完成后进行
    # 206 登录成功, 恭喜，您已通过企业认证审核。认证有效期至xxxx年xx月xx日
    # 208 登录成功, 返回空界面，暂不支持该类手机号
    def login(self, phone, login_verification_code):
        count = 1
        status = None
        status_code = None
        message = None
        if self.driver is None:
            status = False
            status_code = 201  # 登录失败! 验证码错误，请重新输入
            message = '登陆失败,浏览器奔溃'
            count = 10

        while count<6:
            print("第{}次登录".format(count))
            try:
                # 点击同意使用条款
                if count == 1:
                    check_button = self.driver.find_element_by_xpath("//input[@class='check-douyin-checkbox']")
                    check_button.click()
                else:
                    # 如果是重新尝试，先检测下是否存在提示按钮
                    time.sleep(2)
                    register_button = self.driver.find_elements_by_xpath("//button[@class='ant-btn register-button']")
                    if register_button:
                        print('检测到  register_button')
                        status = True
                        status_code, message = self.is_login_success(phone=phone)
                        break

                print('login_verification_code  {}'.format(login_verification_code))
                # 填写验证码
                user_code = self.driver.find_element_by_id('mobile-code')
                user_code.clear()
                user_code.send_keys(login_verification_code)
                time.sleep(1)
                # 登录
                login_submit = self.driver.find_element_by_xpath("//button[@id='bytedance-login-submit']")
                login_submit.click()
                time.sleep(5)
                self.driver.refresh()
                time.sleep(3)
                # 这里刷新后可以再转向 https://renzheng.douyin.com/guide?fiji_source=douyin 这个地址
                # 检测 //div[@id='login-switch'] 节点,存在则没登录成功，不存在则登录成功

                # elif len(self.driver.find_elements_by_xpath("//div[@id='mainBox']/div")) == 0:
                #     status = False
                #     status_code = 208
                #     message = self.login_err_code[status_code]
                #     break

                # 1、现判断是否登录成功，通过登录后页面特征判断
                check_username = self.driver.find_elements_by_xpath("//span[@class='user-name']")
                if check_username != []:
                    status = True
                    status_code, message = self.is_login_success(phone=phone)
                    break
                elif self.driver.find_elements_by_xpath("//button[@class='ant-btn register-button']"):
                    print('出现 register_button')
                    status = True
                    status_code, message = self.is_login_success(phone=phone)
                    break
                # self.driver.find_element_by_id('login-msg').get_attribute("style") == 'display: block;':
                elif self.driver.find_element_by_id('login-msg').get_attribute("style") == 'display: block;':
                    login_msg = self.driver.find_element_by_id('login-msg').text
                    if str(login_msg).__contains__('验证码错误，请重新输入'):
                        print("login_msg:", login_msg)
                        status_code = 202  # 登录失败! 验证码错误，请重新输入
                        message = self.login_err_code[status_code]
                        break
                    elif str(login_msg).__contains__('错误次数过多或验证码过期，请稍后重试'):
                        status_code = 203  # 登录失败! 登录验证码过期
                        message = self.login_err_code[status_code]
                        count += 1
                        break
                    elif str(login_msg) == '':
                        print('{} 登陆失败, login_msg是空串'.format(phone))
                        status_code = 201  # 登录失败, 原因未知
                        message = self.login_err_code[status_code] + '抖音提示信息为空串'
                        count += 1
                        continue
                    else:
                        print('{} 登陆失败, login_msg什么都不是'.format(phone))
                        status_code = 201  # 录失败, 原因未知
                        message = self.login_err_code[status_code] + '抖音提示信息为: {}'.format(login_msg)
                        count += 1
                        continue
                else:
                    print("没有username, 没有register_button, login-msg也不是display: block;")
                    status_code = 201  # 登录失败, 原因未知
                    message = self.login_err_code[status_code] + '没有username, 没有register_button, login-msg也不是display: block;'
                    count += 1
                    continue
            except Exception as e:
                if len(self.driver.find_elements_by_xpath("//div[@id='mainBox']")) == 1 \
                        and len(self.driver.find_elements_by_xpath("//div[@id='mainBox']/div")) == 0:
                    print("登陆成功，不支持该类手机号")
                    status = False
                    status_code = 208
                    message = self.login_err_code[status_code]
                    break
                else:
                    print('{} 登录出现异常 {}'.format(phone, e))
                    count += 1
                    status_code = 201  # 录失败, 原因未知
                    message = self.login_err_code[status_code]
                    continue
        time.sleep(1)
        cookies = self.driver.get_cookies()

        result = {
            'status': status,
            'status_code': status_code,
            'message': message,
            'login_cookies': cookies
        }
        print('{} login {}'.format(phone, result))
        return result

    '''
        200: '蓝V认证验证码发送成功',
        201: '蓝V认证验证码发送失败, 原因未知',
        202: '蓝V认证验证码发送失败, 用户当前社区状态不能申请企业认证',
        203: '蓝V认证验证码发送失败, 认证资料缺失',
        204: '蓝V认证验证码发送失败, 认证资中用户昵称校验不可用',
        205: '蓝V认证验证码发送失败, 填写用户昵称发生异常',
        206: '蓝V认证验证码发送失败, 填写认证信息发生异常',
        207: '蓝V认证验证码发送失败, 不存在的一级行业类型',
        208: '蓝V认证验证码发送失败, 填写一级行业类型发生异常',
        209: '蓝V认证验证码发送失败, 不存在的二级行业类型或二级行业与一级行业不匹配',
        210: '蓝V认证验证码发送失败, 填写二级行业类型发生异常',
        211: '蓝V认证验证码发送失败, 上传企业营业执照图发生异常',
        212: '蓝V认证验证码发送失败, 上传认证申请公函图片发生异常',
        213: '蓝V认证验证码发送失败, 上传其他资质图片发生异常',
        214: '蓝V认证验证码发送失败, 填写运营者名称发生异常',
        215: '蓝V认证验证码发送失败, 填写运营者手机号码发生异常',
        216: '蓝V认证验证码发送失败, 填写运营者电子邮箱发生异常',
        217: '蓝V认证验证码发送失败, 填写发票接收电子邮箱发生异常',
        218: '蓝V认证验证码发送失败, 填写开户银行发生异常',
        219: '蓝V认证验证码发送失败, 填写银行账号发生异常',
        220: '蓝V认证验证码发送失败, 填写企业地址异常',
        221: '蓝V认证验证码发送失败, 填写企业电话异常',
        222: '# 蓝V认证验证码发送失败, 填写邀请码发生异常',
        223: '蓝V认证验证码发送失败, 点击同意并遵守异常',
        224: '蓝V认证验证码发送失败, 拖动滚动条到验证码按钮附近异常',
        225: '蓝V认证验证码发送失败, 输入信息检测出现无效输入,提示信息为:',
        226: '蓝V认证验证码发送失败, 判断输入是否有效发生异常',
        227: '蓝V认证验证码发送失败, 点击发送蓝V认证验证码发生异常',
        228: '蓝V认证验证码发送失败, 验证码发送失败',
        229: '企业认证资料已成功提交，请支付审核服务费。认证审核将会在支付完成后进行',
        230: '恭喜，您已通过企业认证审核。认证有效期至xxxx年xx月xx日'
    '''
    def send_auth_verifica_code(self, phone, cookies):
        is_continue, status, status_code, message = self._init_driver(phone=phone, cookies=cookies)
        if not is_continue:
            return {'status': status, 'status_code': status_code,
                    'message': message, 'send_auth_verifica_code_time': None}

        self._click_auth()
        auth_path = PATH + phone + '/auth.json'
        print("auth_path is {}".format(auth_path))
        load_f = open(auth_path, 'r', encoding='UTF-8')
        auth_param = json.load(load_f)
        load_f.close()

        total_count = 1
        send_auth_verifica_code_time = None
        while total_count < 5:
            self.driver.get(url='https://renzheng.douyin.com/register')
            time.sleep(5)
            print("第{}次填写认证信息".format(total_count))
            try:
                # 用户名称
                if 'nick_name' in auth_param:
                    nick_name = auth_param['nick_name']
                    cookies = self.get_cookies()
                    fill_result, err_reason = robots_utils.fill_nick_name(driver=self.driver, cookies=cookies,
                                                             phone=phone, nick_name=nick_name)
                    if fill_result == 1:
                        print('{} nick_name 填写成功')
                    elif fill_result == -1:
                        print('{} 填写 nick_name 不可用'.format(phone))
                        status = False
                        status_code = 204  # 蓝V认证验证码发送失败, 认证资中用户昵称校验不可用
                        # 蓝V认证验证码发送失败, 认证资中用户昵称校验不可用
                        message = self.auth_err_code_dict[status_code] + ',抖音提示信息为: {}'.format(err_reason)
                        break
                    elif fill_result == -2:
                        print('{} 填写 nick_name 异常'.format(phone))
                        status = False
                        status_code = 205  # 蓝V认证验证码发送失败, 填写用户昵称发生异常
                        message = self.auth_err_code_dict[status_code]  # 蓝V认证验证码发送失败, 填写用户昵称发生异常
                        total_count += 1
                        continue
                else:
                    print("提交资料中没有 nick_name")
                    status = False
                    status_code = 203  # 蓝V认证验证码发送失败,认证资料缺失
                    message = self.auth_err_code_dict[status_code] + ',问题定位在 nick_name'  # 蓝V认证验证码发送失败, 认证资料缺失
                    break

                # 认证信息
                if 'auth_info' in auth_param:
                    auth_info = auth_param['auth_info']
                    fill_result = robots_utils.fill_auth_info(driver=self.driver, phone=phone, auth_info=auth_info)
                    if fill_result:
                        print('{} auth_info 填写成功'.format(phone))
                    else:
                        print('{} auth_info 填写失败'.format(phone))

                        status = False
                        status_code = 206  # 蓝V认证验证码发送失败, 填写认证信息发生异常
                        message = self.auth_err_code_dict[status_code]

                        total_count += 1
                        continue
                else:
                    print("提交资料中没有 auth_info")
                    status = False
                    status_code = 203  # 蓝V认证验证码发送失败,认证资料缺失
                    message = self.auth_err_code_dict[status_code] + ',问题定位在 auth_info'  # 蓝V认证验证码发送失败, 认证资料缺失
                    break

                # 一级行业信息
                if 'first_classification' in auth_param:   # 先检测提交资料中是否包含一级行业信息
                    first_classification = auth_param['first_classification']
                    # 再检测一级行业信息是否规范
                    first_code, first_type_choose = common.get_first_classification(first_classification)
                    if first_code is False:
                        status = False
                        status_code = 207  # 蓝V认证验证码发送失败, 不存在的一级行业类型
                        message = self.auth_err_code_dict[status_code] + \
                                            ",请从以下内容中选取一级行业:{}".format(str(first_type_choose))
                        break

                    fill_result = robots_utils.fill_first_type_trade(driver=self.driver, phone=phone,
                                                                     first_classification=first_classification)
                    if fill_result:
                        print('{} first_classification 填写成功')
                    else:
                        print('{} first_classification 填写失败')
                        status = False
                        status_code = 208  # 蓝V认证验证码发送失败, 填写一级行业类型发生异常
                        message = self.auth_err_code_dict[status_code]
                        total_count += 1
                        continue
                else:
                    print("提交资料中没有 first_classification")
                    status = False
                    status_code = 203  # 蓝V认证验证码发送失败,认证资料缺失
                    # 蓝V认证验证码发送失败, 认证资料缺失
                    message = self.auth_err_code_dict[status_code] + ',问题定位在 first_classification'
                    send_auth_verifica_code_time = None
                    break

                time.sleep(1)

                # 二级行业信息
                if 'second_classification' in auth_param:  # 先检测提交资料中是否包含二级行业信息
                    second_classification = auth_param['second_classification']
                    # 再检测二级行业信息是否与一级行业信息对应
                    second_type_choose = common.get_second_classification(first_code, self.cookies,
                                                                          second_classification)
                    if isinstance(second_type_choose, int) is False:
                        status = False
                        status_code = 209  # 蓝V认证验证码发送失败, 不存在的二级行业类型或二级行业与一级行业不匹配
                        message = self.auth_err_code_dict[status_code] + \
                                  ",请从以下内容中选取二级行业:{}".format(str(second_type_choose))
                        break

                    fill_result = robots_utils.fill_second_type_trade(driver=self.driver, phone=phone,
                                                                      second_classification=second_classification)
                    if fill_result:
                        print('{} second_classification 填写成功'.format(phone))
                    else:
                        print('{} second_classification 填写失败'.format(phone))
                        status = False
                        status_code = 210  # 蓝V认证验证码发送失败, 填写二级行业类型发生异常
                        message = self.auth_err_code_dict[status_code]
                        total_count += 1
                        continue
                else:
                    print("提交资料中没有 second_classification")
                    status = False
                    status_code = 203  # 蓝V认证验证码发送失败,认证资料缺失
                    message = self.auth_err_code_dict[status_code] + ',问题定位在 second_classification'
                    break

                time.sleep(1)

                # 企业营业执照信息
                try:
                    pre_business_license_path = os.path.join(PATH, auth_param['phone'], "pre_business_license.jpg")
                    if os.path.exists(pre_business_license_path):
                        business_license = self.driver.find_element_by_xpath(
                            "//div[@class='ant-row ant-form-item'][4]//input[@type='file']")
                        business_license.send_keys(pre_business_license_path)
                        time.sleep(3)
                        print('{} 上传企业营业执照图片 成功'.format(phone))
                    else:
                        print("企业营业执照图片不存在")
                        status = False
                        status_code = 203  # 蓝V认证验证码发送失败,认证资料缺失
                        message = self.auth_err_code_dict[status_code] + ',问题定位在企业营业执照图片不存在'
                        break
                except Exception as e:
                    print('{} 上传企业营业执照图片 异常 {}'.format(phone, e))
                    status = False
                    status_code = 211  # 蓝V认证验证码发送失败, 上传企业营业执照图发生异常
                    message = self.auth_err_code_dict[status_code]
                    total_count += 1
                    continue

                # 认证申请公函信息
                try:
                    pre_certification_application_path = os.path.join(PATH, auth_param['phone'],
                                                                      "pre_certification_application.jpg")
                    check_jpeg = common.check_certification(cookies=self.cookies,
                                                            file_path=pre_certification_application_path)
                    if check_jpeg is False:
                        status = False
                        status_code = 212  # 蓝V认证验证码发送失败,认证资料缺失
                        message = '认证申请公函图片不合规'
                        break
                    if os.path.exists(pre_certification_application_path):
                        certification_application = self.driver.find_element_by_xpath(
                            "//div[@class='ant-row ant-form-item'][5]//input[@type='file']")
                        certification_application.send_keys(pre_certification_application_path)
                        time.sleep(3)
                        print('{} 上传申请公函图片 成功'.format(phone))
                    else:
                        print("认证申请公函图片不存在")
                        status = False
                        status_code = 203  # 蓝V认证验证码发送失败,认证资料缺失
                        message = self.auth_err_code_dict[status_code] + ',问题定位在认证申请公函图片不存在'
                        send_auth_verifica_code_time = None
                        break
                except Exception as e:
                    print('{} 上传认证申请公函图片 异常 {}'.format(phone, e))
                    status = False
                    status_code = 212  # 蓝V认证验证码发送失败, 上传认证申请公函图片发生异常
                    message = self.auth_err_code_dict[status_code]
                    total_count += 1
                    continue

                # 其它资质
                try:
                    pre_other_qualifications_path = os.path.join(PATH, auth_param['phone'],
                                                                 "pre_other_qualifications.jpg")
                    if os.path.exists(pre_other_qualifications_path):
                        other_qualifications = self.driver.find_element_by_xpath(
                            "//div[@class='ant-row ant-form-item'][6]//input[@type='file']")
                        other_qualifications.send_keys(pre_other_qualifications_path)
                        print('上传其他资质信息成功')
                    else:
                        print('{} 未提供其他资质信息,不做操作'.format(phone))
                except Exception as e:
                    print('{} 上传其他资质图片 异常 {}'.format(phone, e))
                    status = False
                    status_code = 213  # 蓝V认证验证码发送失败, 上传其他资质图片发生异常
                    message = self.auth_err_code_dict[status_code]
                    total_count += 1
                    continue

                # 运营者名称
                if 'operator_name' in auth_param:
                    operator_name = auth_param['operator_name']
                    fill_result = robots_utils.fill_operator_name(driver=self.driver, phone=phone, operator_name=operator_name)
                    if fill_result:
                        print('{} operator_name 填写成功'.format(phone))
                    else:
                        print('{} operator_name 填写失败'.format(phone))

                        status = False
                        status_code = 214  # 蓝V认证验证码发送失败, 填写运营者名称发生异常
                        message = self.auth_err_code_dict[status_code]

                        total_count += 1
                        continue
                else:
                    print("提交资料中没有 operator_name")
                    status = False
                    status_code = 203  # 蓝V认证验证码发送失败,认证资料缺失
                    message = self.auth_err_code_dict[status_code] + ',问题定位在 operator_name'  # 蓝V认证验证码发送失败, 认证资料缺失
                    send_auth_verifica_code_time = None
                    break

                # 运营者手机号码
                if 'operator_phone' in auth_param:
                    operator_phone = auth_param['operator_phone']
                    fill_result = robots_utils.fill_operator_phone(driver=self.driver, phone=phone, operator_phone=operator_phone)
                    if fill_result:
                        print('{} operator_phone 填写成功'.format(phone))
                    else:
                        print('{} operator_phone 填写失败'.format(phone))

                        status = False
                        status_code = 215  # 蓝V认证验证码发送失败, 填写运营者手机号码发生异常
                        message = self.auth_err_code_dict[status_code]

                        total_count += 1
                        continue
                else:
                    print("提交资料中没有 operator_phone")
                    status = False
                    status_code = 203  # 蓝V认证验证码发送失败,认证资料缺失
                    message = self.auth_err_code_dict[status_code] + ',问题定位在 operator_phone'  # 蓝V认证验证码发送失败, 认证资料缺失
                    send_auth_verifica_code_time = None
                    break

                # 运营者电子邮箱
                if 'operator_mail' in auth_param:
                    operator_mail = auth_param['operator_mail']
                    fill_result = robots_utils.fill_operator_mail(driver=self.driver, phone=phone,
                                                                   operator_mail=operator_mail)
                    if fill_result:
                        print('{} operator_mail 填写成功'.format(phone))
                    else:
                        print('{} operator_mail 填写失败'.format(phone))

                        status = False
                        status_code = 216  # 蓝V认证验证码发送失败, 填写运营者电子邮箱发生异常
                        message = self.auth_err_code_dict[status_code]

                        total_count += 1
                        continue
                else:
                    status = False
                    status_code = 203  # 蓝V认证验证码发送失败,认证资料缺失
                    message = self.auth_err_code_dict[status_code] + ',问题定位在 operator_mail'  # 蓝V认证验证码发送失败, 认证资料缺失
                    send_auth_verifica_code_time = None
                    break

                # 是否索要发票，1是，0否
                if 'invoice_flag' in auth_param:
                    invoice_flag = auth_param['invoice_flag']
                    if invoice_flag == 1:
                        self.driver.find_element_by_xpath("//input[@class='ant-radio-input' and @value='1']").click()
                        # 发票接收电子邮箱
                        try:
                            if 'Invoice_receipt_email' in auth_param:
                                Invoice_receipt_email = auth_param['Invoice_receipt_email']
                                InvoiceReceiptEmail = self.driver.find_element_by_xpath("//input[@id='invoice_mail']")
                                InvoiceReceiptEmail.send_keys(Invoice_receipt_email)
                                print('{} 发票接收电子邮箱 成功')
                            else:
                                status = False
                                status_code = 203  # 蓝V认证验证码发送失败,认证资料缺失
                                message = self.auth_err_code_dict[
                                              status_code] + ',问题定位在发票接收电子邮箱 Invoice_receipt_email'  # 蓝V认证验证码发送失败, 认证资料缺失
                                send_auth_verifica_code_time = None
                                break
                        except Exception as e:
                            print("{} 填写发票接收电子邮箱，异常为{}".format(phone, e))

                            status = False
                            status_code = 217  # 蓝V认证验证码发送失败, 填写发票接收电子邮箱发生异常
                            message = self.auth_err_code_dict[status_code]

                            total_count += 1
                            continue

                        # 点击更多发票信息（非必填）
                        self.driver.find_element_by_xpath("//i[@class='anticon anticon-caret-down']").click()

                        # 开户银行
                        if 'bank' in auth_param:
                            try:
                                bank = auth_param['bank']
                                bank_button = self.driver.find_element_by_xpath("//input[@id='bank']")
                                bank_button.clear()
                                bank_button.send_keys(bank)
                                print('{} 填写开户银行 成功')
                            except Exception as e:
                                print("{} 填写开户银行填写异常，异常为{}".format(phone, e))
                                status = False
                                status_code = 218  # 蓝V认证验证码发送失败, 填写开户银行填写异常
                                message = self.auth_err_code_dict[status_code]
                        else:
                            print('{} 提交资料放弃填写开户银行信息 bank')

                        # 银行账号
                        if 'bank_account' in auth_param:
                            try:
                                bank_account = auth_param['bank_account']
                                bankAccount = self.driver.find_element_by_xpath("//input[@id='bank_account']")
                                bankAccount.clear()
                                bankAccount.send_keys(bank_account)
                                print('{} 填写银行账号 成功')
                            except Exception as e:
                                print("{} 填写银行账号填写异常，异常为{}".format(phone, e))
                                status = False
                                status_code = 219  # 蓝V认证验证码发送失败, 填写银行账号异常
                                message = self.auth_err_code_dict[status_code]
                        else:
                            print('{} 提交资料放弃填写银行账号信息 bank_account')

                        # 企业地址
                        if 'customer_address' in auth_param:
                            try:
                                customer_address = auth_param['customer_address']
                                customerAddress = self.driver.find_element_by_xpath("//input[@id='customer_address']")
                                customerAddress.clear()
                                customerAddress.send_keys(customer_address)
                                print('{} 填写企业地址 成功')
                            except Exception as e:
                                print("{} 企业地址填写异常，异常为{}".format(phone, e))
                                status = False
                                status_code = 220  # 蓝V认证验证码发送失败, 填写企业地址异常
                                message = self.auth_err_code_dict[status_code]
                        else:
                            print('{} 提交资料放弃填写企业地址信息 customer_address')

                        # 企业电话
                        if 'customer_phone' in auth_param:
                            try:
                                customer_phone = auth_param['customer_phone']
                                customerPhone = self.driver.find_element_by_xpath("//input[@id='customer_phone']")
                                customerPhone.clear()
                                customerPhone.send_keys(customer_phone)
                                print('{} 填写企业电话 成功')
                            except Exception as e:
                                print("{} 企业电话填写异常，异常为{}".format(phone, e))
                                status = False
                                status_code = 221  # 蓝V认证验证码发送失败, 填写企业电话异常
                                message = self.auth_err_code_dict[status_code]
                        else:
                            print('{} 提交资料放弃填写企业电话信息 customer_phone')
                    else:
                        # 点击放弃索要发票
                        self.driver.find_element_by_xpath("//input[@class='ant-radio-input' and @value='0']").click()
                else:
                    status = False
                    status_code = 203  # 蓝V认证验证码发送失败,认证资料缺失
                    # 蓝V认证验证码发送失败, 认证资料缺失
                    message = self.auth_err_code_dict[status_code] + ',问题定位在 缺失是否索要发票标准信息 invoice_flag'
                    send_auth_verifica_code_time = None
                    break

                # 邀请码
                if 'agent_code' in auth_param:
                    agent_id = auth_param['agent_code']
                    fill_result = robots_utils.fill_agent_code(driver=self.driver, phone=phone,
                                                                  agent_code=agent_id)
                    if fill_result:
                        print('{} agent_code 填写成功'.format(phone))
                    else:
                        print('{} agent_code 填写失败'.format(phone))

                        status = False
                        status_code = 222  # 蓝V认证验证码发送失败, 填写邀请码发生异常
                        message = self.auth_err_code_dict[status_code]

                        total_count += 1
                        continue
                else:
                    status = False
                    status_code = 203  # 蓝V认证验证码发送失败,认证资料缺失
                    # 蓝V认证验证码发送失败, 认证资料缺失
                    message = self.auth_err_code_dict[status_code] + ',问题定位在 提交资料中没有邀请码 agent_code'
                    send_auth_verifica_code_time = None
                    break

                # 同意并遵守
                try:
                    self.driver.find_element_by_xpath("//input[@type='checkbox' and @id='isAgree']").click()
                    print('{} 点击同意并遵守 成功'.format(phone))
                except Exception as e:
                    print('{} 点击同意并遵守 异常 {}'.format(phone, e))
                    status = False
                    status_code = 223  # 蓝V认证验证码发送失败, 点击同意并遵守异常
                    message = self.auth_err_code_dict[status_code]
                    total_count += 1
                    continue

                # 拖动滚动条到验证码按钮附近
                try:
                    self.driver.execute_script('window.scrollTo(0,800);')
                    print('{} 拖动滚动条到验证码按钮附近 成功'.format(phone))
                except Exception as e:
                    print('{} 拖动滚动条到验证码按钮附近 异常 {}'.format(phone, e))
                    status = False
                    status_code = 224  # 蓝V认证验证码发送失败, 拖动滚动条到验证码按钮附近异常
                    message = self.auth_err_code_dict[status_code]
                    total_count += 1
                    continue

                # 判断输入是否有效
                try:
                    auto_msg_lis = self.driver.find_elements_by_xpath("//div[@class='ant-form-explain']")
                    if auto_msg_lis:
                        for auto_msg_li in auto_msg_lis:
                            print('{} 输入无效，提示信息为 {}'.format(phone, auto_msg_li.text))
                        status = False
                        status_code = 225  # 蓝V认证验证码发送失败, 输入信息检测出现无效输入,提示信息为:
                        message = self.auth_err_code_dict[status_code] + str(auto_msg_lis[0].text)
                        total_count += 1
                        break
                    else:
                        print('{} 输入校验通过'.format(phone))
                except Exception as e:
                    print('{} 判断输入是否有效 异常 {}'.format(phone, e))
                    status = False
                    status_code = 226  # 蓝V认证验证码发送失败, 判断输入是否有效发生异常
                    message = self.auth_err_code_dict[status_code]
                    total_count += 1
                    continue

                # 发送蓝V认证验证码
                try:
                    self.driver.find_element_by_xpath(
                        "//div[@class='ant-row ant-form-item' and @style='overflow: visible;']//button").click()
                    print('{} 点击发送蓝V认证验证码 成功'.format(phone))
                except Exception as e:
                    print('{} 点击发送蓝V认证验证码 异常 {}'.format(phone, e))
                    status = False
                    status_code = 227  # 蓝V认证验证码发送失败, 点击发送蓝V认证验证码发生异常
                    message = self.auth_err_code_dict[status_code]
                    total_count += 1
                    continue

                # 验证码是否发送成功
                try:
                    send_auth_code_li = self.driver.find_elements_by_xpath(
                        "//div[@class='ant-row ant-form-item' and @style='overflow: visible;']"
                        "//button[@class='ant-btn fiji-guide-button']/span")
                    if send_auth_code_li:
                        send_auth_code_msg = send_auth_code_li[0].text
                        if send_auth_code_msg == '获取验证码':
                            print('验证码发送失败')
                            status = False
                            status_code = 228  # 蓝V认证验证码发送失败, 验证码发送失败
                            message = self.auth_err_code_dict[status_code]
                            total_count += 1
                            continue
                        else:
                            print('验证码发送成功')
                except Exception as e:
                    print('{} 验证码是否发送出现异常 {}'.format(phone, e))
                    status = False
                    status_code = 236  # 蓝V认证验证码发送失败, 检测验证码是否发送成功发生异常
                    message = self.auth_err_code_dict[status_code]
                    total_count += 1
                    continue

                # 发送成功，返回当前时间
                status = True
                status_code = 200
                message = self.auth_err_code_dict[status_code]
                send_auth_verifica_code_time = int(round(time.time() * 1000))
                break
            except Exception as e:
                print(e)
                self.refresh()

                status = False
                status_code = 201  # 蓝V认证验证码发送失败, 原因未知
                message = message = self.auth_err_code_dict[status_code]

                total_count += 1
                continue

        result = {
            'status': status,
            'status_code': status_code,
            'message': message,
            'send_auth_verifica_code_time': send_auth_verifica_code_time
        }
        print('{} login {}'.format(phone, result))
        return result

    '''
    发送蓝V验证码之前，初始化浏览器
    '''
    def _init_driver(self, phone, cookies):
        is_continue = None
        status = None
        status_code = None
        message = None
        try:
            if self.driver is None:
                print("driver is None,try add cookie and openDriver")
                self.openDriver()
                # 这里打开可能是已经完成认证的
                # 也有可能是已提交资料待付款的
                # 还有可能是社区用户不能认证的
                self.driver.get(url='https://renzheng.douyin.com/guide?fiji_source=douyin')
                time.sleep(1)
                self.driver.delete_all_cookies()
                for cookie in cookies:
                    if 'expiry' in cookie:
                        del cookie['expiry']
                    self.driver.add_cookie(cookie)
                self.driver.get(url='https://renzheng.douyin.com/guide?fiji_source=douyin')
                time.sleep(3)
                self.cookies = self.get_cookies()
                if self._is_possible_auth(phone=phone):
                    is_continue = True
                else:
                    is_continue = False
                    status = False
                    status_code = 202  # 用户当前社区状态不能申请企业认证
                    message = self.auth_err_code_dict[status_code]

                if is_continue:
                    if self._is_pay(phone=phone):
                        is_continue = False
                        status = False
                        status_code = 229  # 企业认证资料已成功提交，请支付审核服务费。认证审核将会在支付完成后进行
                        message = self.auth_err_code_dict[status_code]
                    else:
                        is_continue = True

                if is_continue:
                    finsh_flag, msg = self._is_finsh(phone=phone)
                    if finsh_flag:
                        is_continue = False
                        status = False
                        status_code = 230  # 恭喜，您已通过企业认证审核。认证有效期至xxxx年xx月xx日
                        message = msg
                    else:
                        is_continue = True
            else:
                # 发验证码之前刷新下页面，确保浏览器处在填写认证信息的页面
                self.driver.delete_all_cookies()
                for cookie in cookies:
                    if 'expiry' in cookie:
                        del cookie['expiry']
                    self.driver.add_cookie(cookie)
                self.driver.get(url='https://renzheng.douyin.com/guide?fiji_source=douyin')
                time.sleep(3)
                self.cookies = self.get_cookies()
                if self._is_possible_auth(phone=phone):
                    is_continue = True
                else:
                    is_continue = False
                    status = False
                    status_code = 202  # 用户当前社区状态不能申请企业认证
                    message = self.auth_err_code_dict[status_code]

                if is_continue:
                    if self._is_pay(phone=phone):
                        is_continue = False
                        status = False
                        status_code = 229  # 企业认证资料已成功提交，请支付审核服务费。认证审核将会在支付完成后进行
                        message = self.auth_err_code_dict[status_code]
                    else:
                        is_continue = True

                if is_continue:
                    finsh_flag, msg = self._is_finsh(phone=phone)
                    if finsh_flag:
                        is_continue = False
                        status = False
                        status_code = 230  # 恭喜，您已通过企业认证审核。认证有效期至xxxx年xx月xx日
                        message = msg
                    else:
                        is_continue = True
        except Exception as e:
            print('初始化浏览器异常 {}'.format(e))
            is_continue = False
            status = False
            status_code = 201  # 蓝V认证验证码发送失败, 原因未知
            message = self.auth_err_code_dict[status_code]  # '蓝V认证验证码发送失败,初始化浏览器异常,原因未知'
        return is_continue, status, status_code, message

    def _is_finsh(self, phone):
        try:
            status_flag_ele = self.driver.find_element_by_xpath(
                "//div[@class='douyin-platform fiji-guide-guide-status']//div[@class='content']"
                "/p[@class='content-title']")
            if status_flag_ele:
                status_flag_text = status_flag_ele.text
                if str(status_flag_text).__contains__('审核通过'):
                    msg = self.driver.find_element_by_xpath(
                "//div[@class='douyin-platform fiji-guide-guide-status']//div[@class='content']"
                "/p[@class='content-description']").text
                    print('{}  {}'.format(phone, msg))
                    return True, msg
                else:
                    print('{}  {}'.format(phone, status_flag_text))
                    return False, None
            else:
                print('{}  status_flag_ele is {}'.format(phone, status_flag_ele))
        except Exception as e:
            print("{} 检测是否完成认证时发生异常 {}".format(phone, e))

    def _is_pay(self, phone):
        try:
            pay_flag_ele = self.driver.find_element_by_xpath("//button[@class='ant-btn register-button']")
            if pay_flag_ele:
                pay_flag_text = pay_flag_ele.text
                if str(pay_flag_text).__contains__('立即付款'):
                    print('{}  企业认证资料已成功提交，请支付审核服务费。认证审核将会在支付完成后进行'.format(phone))
                    return True
                else:
                    return False
        except Exception as e:
            print("{} 检测是否付款时发生异常 {}".format(phone, e))

    '''
    探测该账号是否可以认证(有的账号登上去显示用户社区状态下不能申请企业认证)
    '''
    def _is_possible_auth(self, phone):
        error_code = self.driver.find_elements_by_xpath("//div[@class='error-code']")
        if error_code != []:
            print('{}  登录成功但用户当前社区状态不能申请企业认证'.format(phone))
            return False
        else:
            return True

    def _click_auth(self):
        register_count=1
        while register_count<6:
            print("第{}次点击立即认证".format(register_count))
            # 立即认证
            try:
                register_button = self.driver.find_element_by_xpath("//button[@class='ant-btn register-button']")
                register_button.click()
                break
            except Exception as e:
                print("点击立即认证异常 {}".format(e))
                time.sleep(3)
            register_count += 1

        time.sleep(3)
        self.cookies = self.get_cookies()

    def _init_err_code(self):
        # 200 登录成功
        # 201 登录失败, 原因未知
        # 202 登陆失败, 登录验证码错误
        # 203 登录失败, 验证码过期
        # 204 登录成功, 用户当前社区状态不能申请企业认证
        # 205 登录成功, 企业认证资料已成功提交，请支付审核服务费。认证审核将会在支付完成后进行
        # 206 登录成功, 恭喜，您已通过企业认证审核。认证有效期至xxxx年xx月xx日
        self.login_err_code = {
            200: '登录成功',
            201: '登录失败, 原因未知',
            202: '登陆失败, 登录验证码错误',
            203: '登录失败, 验证码过期',
            204: '登录成功, 用户当前社区状态不能申请企业认证',
            205: '登录成功, 企业认证资料已成功提交，请支付审核服务费。认证审核将会在支付完成后进行',
            206: '登录成功, 恭喜，您已通过企业认证审核。认证有效期至xxxx年xx月xx日',
            207: '登陆失败, 该手机号不支持蓝V认证。',
            208: '登录成功, 返回空界面，暂不支持该类手机号。',
            209: '登陆失败, 验证码发送太频繁,请稍后再试。',
            210: '登陆失败, 提示信息还没见过。',
            211: '登陆失败, 滑动验证码验证失败。'
        }
        self.auth_err_code_dict = {
            200: '蓝V认证验证码发送成功',
            201: '蓝V认证验证码发送失败, 原因未知',
            202: '蓝V认证验证码发送失败, 用户当前社区状态不能申请企业认证',
            203: '蓝V认证验证码发送失败, 认证资料缺失',
            204: '蓝V认证验证码发送失败, 认证资中用户昵称校验不可用',
            205: '蓝V认证验证码发送失败, 填写用户昵称发生异常',
            206: '蓝V认证验证码发送失败, 填写认证信息发生异常',
            207: '蓝V认证验证码发送失败, 不存在的一级行业类型',
            208: '蓝V认证验证码发送失败, 填写一级行业类型发生异常',
            209: '蓝V认证验证码发送失败, 不存在的二级行业类型或二级行业与一级行业不匹配',
            210: '蓝V认证验证码发送失败, 填写二级行业类型发生异常',
            211: '蓝V认证验证码发送失败, 上传企业营业执照图发生异常',
            212: '蓝V认证验证码发送失败, 上传认证申请公函图片发生异常',
            213: '蓝V认证验证码发送失败, 上传其他资质图片发生异常',
            214: '蓝V认证验证码发送失败, 填写运营者名称发生异常',
            215: '蓝V认证验证码发送失败, 填写运营者手机号码发生异常',
            216: '蓝V认证验证码发送失败, 填写运营者电子邮箱发生异常',
            217: '蓝V认证验证码发送失败, 填写发票接收电子邮箱发生异常',
            218: '蓝V认证验证码发送失败, 填写开户银行发生异常',
            219: '蓝V认证验证码发送失败, 填写银行账号发生异常',
            220: '蓝V认证验证码发送失败, 填写企业地址异常',
            221: '蓝V认证验证码发送失败, 填写企业电话异常',
            222: '# 蓝V认证验证码发送失败, 填写邀请码发生异常',
            223: '蓝V认证验证码发送失败, 点击同意并遵守异常',
            224: '蓝V认证验证码发送失败, 拖动滚动条到验证码按钮附近异常',
            225: '蓝V认证验证码发送失败, 输入信息检测出现无效输入,提示信息为:',
            226: '蓝V认证验证码发送失败, 判断输入是否有效发生异常',
            227: '蓝V认证验证码发送失败, 点击发送蓝V认证验证码发生异常',
            228: '蓝V认证验证码发送失败, 验证码发送失败',
            229: '企业认证资料已成功提交，请支付审核服务费。认证审核将会在支付完成后进行',
            230: '恭喜，您已通过企业认证审核。认证有效期至xxxx年xx月xx日',
            231: '蓝V认证验证码提交失败, 点击提交资料爬虫出现异常',
            232: '蓝V认证验证码提交失败, 失败信息为: 运营手机号超过上限，请更换。',
            233: '蓝V认证验证码提交失败, 失败信息为: 校验失败。',
            234: '蓝V认证验证码提交失败, 失败信息为: 验证码验证次数过多。',
            235: '蓝V认证验证码提交失败, 失败原因未知,',
            236: '蓝V认证验证码发送失败, 检测验证码是否发送成功发生异常'
        }

if __name__ == '__main__':
    phone = '15580859663'
    # phone = '17375762570'

    cookies = [{'domain': '.renzheng.douyin.com', 'expiry': 1594231245.690113, 'httpOnly': False, 'name': 'SLARDAR_WEB_ID', 'path': '/', 'secure': False, 'value': '50973d70-7196-4cc0-95df-0cc2798a9922'}, {'domain': '.renzheng.douyin.com', 'expiry': 1589047246.443485, 'httpOnly': True, 'name': 'fiji-guide-session-douyin', 'path': '/', 'secure': False, 'value': 'fiji-guide-session-douyin545d5093-0f31-4c03-aa61-bc879745cc06'}, {'domain': '.douyin.com', 'expiry': 1591639240.634934, 'httpOnly': True, 'name': 'toutiao_sso_user', 'path': '/', 'secure': False, 'value': '56ebf07f48e2f712bcd9cccf0e35bd6e'}, {'domain': '.douyin.com', 'expiry': 1591639240.634946, 'httpOnly': True, 'name': 'toutiao_sso_user_ss', 'path': '/', 'sameSite': 'None', 'secure': True, 'value': '56ebf07f48e2f712bcd9cccf0e35bd6e'}, {'domain': '.douyin.com', 'expiry': 1591639240.634903, 'httpOnly': True, 'name': 'sso_uid_tt_ss', 'path': '/', 'sameSite': 'None', 'secure': True, 'value': 'cca593ef36ede05a0a39d8f2e3e1badd'}, {'domain': '.douyin.com', 'expiry': 1591639240.63489, 'httpOnly': True, 'name': 'sso_uid_tt', 'path': '/', 'secure': False, 'value': 'cca593ef36ede05a0a39d8f2e3e1badd'}, {'domain': '.douyin.com', 'expiry': 1589047240.634874, 'httpOnly': True, 'name': 'sso_auth_status', 'path': '/', 'secure': False, 'value': 'e4ff50e89cfa489f880fbf3f14910de9'}, {'domain': '.douyin.com', 'expiry': 1589047240.634775, 'httpOnly': True, 'name': 'passport_auth_status', 'path': '/', 'secure': False, 'value': 'c016a650315c68a44ff4adbdfb30886f%2C'}, {'domain': '.douyin.com', 'expiry': 1586462382.804067, 'httpOnly': False, 'name': 'passport_csrf_token', 'path': '/', 'secure': False, 'value': '9906b96f478f5c79f0a06e38e494fae4'}]


    bot = robot()

    # result = bot.send_login_verifica_code(phone=phone)
    # print('send_login_verifica_code: {}'.format(result))
    #
    # login_verification_code = input()
    # result = bot.login(phone=phone, login_verification_code=login_verification_code)
    # print('login:    {}'.format(result))



    result = bot.send_auth_verifica_code(phone=phone, cookies=cookies)
    print('send_auth_verifica_code: {}'.format(result))
    auth_verifica_code = input()
    result = bot.submit_auth_data(phone=phone,auth_verifica_code=auth_verifica_code,  cookies=cookies)
    print('submit_auth_data: {}'.format(result))
