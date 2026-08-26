# -*- coding: utf-8 -*-
"""Debug: tai sao _try_get_otp_gmail_app bao Non-Gmail cho mail @gmail.com?"""
import sys
sys.path.insert(0, r"D:\Taadaa\Tiktok_Reg")
import social_reg_v1

email = "tranthimy150820011508@gmail.com"
print("endswith check:", email.lower().endswith("@gmail.com"))
print("func module:", social_reg_v1._try_get_otp_gmail_app.__module__)
import inspect
src = inspect.getsource(social_reg_v1._try_get_otp_gmail_app)
print("first 300 chars:")
print(src[:300])
