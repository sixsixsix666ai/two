import streamlit as st
import requests
import json
import base64
import time
import logging
from PIL import Image
from io import BytesIO

# 配置日志记录
logging.basicConfig(level=logging.DEBUG)

# API 密钥（替换为你的真实密钥）
STABILITY_API_KEY = "sk-drvRI8SfNEUPUYr2nTLDFVc6fPi4Ng5n6dDIhntYUeVjlrSa"
HEYGEN_API_KEY = "ZTA2Y2FiYjY5NWMyNDg2MmE1ZTkzNzZiZWQyMTRlYmMtMTc0NTk0MzEwNw=="

# 检查 API 密钥是否已设置
if not STABILITY_API_KEY or not HEYGEN_API_KEY:
    st.error("请确保已正确设置 Stability AI 和 HeyGen 的 API 密钥。")
    st.stop()

class StabilityAIDiagnostic:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip()
        self.base_url = "https://api.stability.ai"
        self.text_to_image_endpoint = f"{self.base_url}/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        self.engines_endpoint = f"{self.base_url}/v1/engines/list"

    def _validate_api_key(self) -> bool:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        try:
            response = requests.get(self.engines_endpoint, headers=headers, timeout=10)
            if response.status_code == 200:
                engines = response.json()
                if len(engines) > 0:
                    st.success(f"[API密钥有效] 检测到可用模型: {', '.join([eng['id'] for eng in engines[:2]])}")
                    return True
            elif response.status_code == 401:
                st.error("[错误] API密钥无效或未授权，请检查密钥是否正确")
            else:
                st.error(f"[错误] 验证失败，状态码: {response.status_code}")
            return False
        except requests.exceptions.RequestException as e:
            st.error(f"[网络错误] 验证API密钥失败: {str(e)}")
            return False

    def generate_image(self, prompt: str, width=1024, height=1024) -> bytes:
        """使用Stability AI生成图像"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        data = {
            "text_prompts": [{"text": prompt}],
            "width": width,
            "height": height,
            "samples": 1,
            "steps": 30,
            "cfg_scale": 7.0,
            "output_format": "png"
        }
        
        with st.spinner("正在使用Stability AI生成图像..."):
            try:
                response = requests.post(
                    self.text_to_image_endpoint,
                    headers=headers,
                    json=data,
                    timeout=120
                )
                if response.status_code != 200:
                    st.error(f"[请求失败] 状态码: {response.status_code}")
                    st.error(f"错误内容: {response.text}")
                    return None
                
                data = response.json()
                if "artifacts" not in data or len(data["artifacts"]) == 0:
                    st.error("[错误] 响应中未包含图像数据")
                    return None
                
                image_data = base64.b64decode(data["artifacts"][0]["base64"])
                st.success(f"[成功] 图像生成完成")
                return image_data
            except requests.exceptions.RequestException as e:
                st.error(f"[请求异常] 图像生成失败: {str(e)}")
                return None
            except base64.binascii.Error as e:
                st.error(f"[数据解析错误] 图像数据解码失败: {str(e)}")
                return None

# HeyGen API 类
class HeyGenAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip()
        self.base_url = "https://api.heygen.com/v2"
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def upload_avatar(self, image_data: bytes, name: str) -> str:
        """上传自定义头像到HeyGen"""
        url = f"{self.base_url}/characters/avatar"
        
        # 将图像数据转换为Base64
        base64_image = base64.b64encode(image_data).decode("utf-8")
        
        data = {
            "name": name,
            "avatar_image": base64_image
        }
        
        with st.spinner("正在上传头像到HeyGen..."):
            try:
                response = requests.post(url, headers=self.headers, json=data)
                if response.status_code == 200:
                    result = response.json()
                    avatar_id = result.get("avatar_id")
                    st.success(f"[成功] 头像上传完成，ID: {avatar_id}")
                    return avatar_id
                else:
                    st.error(f"[错误] 上传头像失败: {response.text}")
                    return None
            except Exception as e:
                st.error(f"[异常] 上传头像时出错: {str(e)}")
                return None
    
    def generate_video(self, avatar_id: str, script: str, background_url: str = None) -> str:
        """使用HeyGen生成视频"""
        url = f"{self.base_url}/video/generate"
        
        # 构建视频生成请求
        video_input = {
            "character": {
                "type": "avatar",
                "avatar_id": avatar_id,
                "avatar_style": "normal"
            },
            "voice": {
                "type": "text",
                "input_text": script,
                "voice_id": "2d5b0e6cf36f460aa7fc47e3eee4ba54"  # 默认语音
            }
        }
        
        # 添加背景（如果有）
        if background_url:
            video_input["background"] = {
                "type": "image",
                "value": background_url
            }
        else:
            video_input["background"] = {
                "type": "color",
                "value": "#ffffff"
            }
        
        data = {
            "video_inputs": [video_input],
            "dimension": {
                "width": 1280,
                "height": 720
            }
        }
        
        with st.spinner("正在生成视频..."):
            try:
                response = requests.post(url, headers=self.headers, json=data)
                if response.status_code == 200:
                    result = response.json()
                    video_id = result.get("video_id")
                    st.info(f"[成功] 视频生成任务已提交，ID: {video_id}")
                    return video_id
                else:
                    st.error(f"[错误] 生成视频失败: {response.text}")
                    return None
            except Exception as e:
                st.error(f"[异常] 生成视频时出错: {str(e)}")
                return None
    
    def check_video_status(self, video_id: str) -> dict:
        """检查视频生成状态"""
        url = f"{self.base_url}/videos/{video_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"[错误] 查询视频状态失败: {response.text}")
                return None
        except Exception as e:
            st.error(f"[异常] 查询视频状态时出错: {str(e)}")
            return None

# Streamlit 界面
st.title("AI虚拟人视频生成器")
st.subheader("上传3-10张人物照片，结合Stability AI的场景生成和HeyGen的人物视频技术")

# 初始化API客户端
stability_client = StabilityAIDiagnostic(STABILITY_API_KEY)
heygen_client = HeyGenAPI(HEYGEN_API_KEY)

# 验证API密钥
if st.button("验证API密钥"):
    with st.spinner("正在验证API密钥..."):
        stability_valid = stability_client._validate_api_key()
        if stability_valid:
            st.success("Stability AI API密钥验证通过")
        else:
            st.error("Stability AI API密钥验证失败")

# 上传人物照片
st.header("1. 上传人物照片")
st.write("请上传3-10张清晰的人物照片，包括正脸、侧身、正面全身照等多角度照片。")

uploaded_files = st.file_uploader(
    "选择人物照片",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

# 检查上传的照片数量
if uploaded_files:
    if len(uploaded_files) < 3:
        st.warning("请上传至少3张照片")
    elif len(uploaded_files) > 10:
        st.warning("最多只能上传10张照片")
    else:
        st.success(f"已上传{len(uploaded_files)}张照片")
        
        # 显示上传的照片
        st.subheader("已上传的照片：")
        for i, file in enumerate(uploaded_files):
            img = Image.open(file)
            st.image(img, caption=f"照片 {i+1}", use_column_width=True)

# 场景描述
st.header("2. 描述场景和服装")
scene_prompt = st.text_area(
    "描述场景和服装",
    "一个现代化的办公室，阳光透过窗户洒在木质地板上。人物穿着时尚的商务装，面带微笑。"
)

# 视频脚本
st.header("3. 输入视频脚本")
video_script = st.text_area(
    "输入视频脚本",
    "大家好，欢迎来到我们的产品发布会。今天我将为大家介绍一款革命性的新产品..."
)

# 生成按钮
if st.button("生成视频"):
    if not uploaded_files or len(uploaded_files) < 3 or len(uploaded_files) > 10:
        st.error("请上传3-10张人物照片")
        st.stop()
    
    if not scene_prompt:
        st.error("请描述场景和服装")
        st.stop()
    
    if not video_script:
        st.error("请输入视频脚本")
        st.stop()
    
    # 1. 使用Stability AI生成场景和服装
    st.subheader("生成场景和服装...")
    scene_image_data = stability_client.generate_image(scene_prompt)
    
    if not scene_image_data:
        st.error("场景生成失败，无法继续")
        st.stop()
    
    # 显示生成的场景
    scene_image = Image.open(BytesIO(scene_image_data))
    st.image(scene_image, caption="生成的场景", use_column_width=True)
    
    # 2. 上传第一张人物照片到HeyGen（只需要一个头像）
    st.subheader("上传人物照片到HeyGen...")
    first_file = uploaded_files[0]
    avatar_name = f"user_avatar_{int(time.time())}"
    avatar_id = heygen_client.upload_avatar(first_file.getvalue(), avatar_name)
    
    if not avatar_id:
        st.error("头像上传失败，无法继续")
        st.stop()
    
    # 3. 准备视频生成
    st.subheader("准备视频生成...")
    # 注意：实际应用中，你需要先将场景图片上传到HeyGen的媒体库
    # 此处简化处理，使用示例背景
    background_url = None  # 示例：如果有上传的背景URL，可以在这里设置
    
    # 4. 生成视频
    st.subheader("开始生成视频...")
    video_id = heygen_client.generate_video(avatar_id, video_script, background_url)
    
    if video_id:
        # 5. 轮询检查视频状态
        max_attempts = 30  # 最多尝试30次
        st.subheader("等待视频生成完成...")
        
        for attempt in range(max_attempts):
            st.write(f"检查状态 ({attempt+1}/{max_attempts})...")
            status_data = heygen_client.check_video_status(video_id)
            
            if not status_data:
                st.warning("无法获取视频状态，可能需要稍后手动检查")
                break
            
            status = status_data.get("status")
            st.write(f"当前状态: {status}")
            
            if status == "completed":
                st.success("视频生成完成！")
                st.video(status_data.get("video_url"))
                break
            elif status == "failed":
                st.error(f"视频生成失败: {status_data.get('message')}")
                break
            
            time.sleep(10)  # 等待10秒再检查
        
        else:
            st.warning("视频生成超时，请在HeyGen平台查看结果")
