from django.shortcuts import render
from django.http import HttpResponse
from .forms import OrderForm,CreationUser
from django.shortcuts import render, redirect
from django.contrib import auth
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from .models import Profile,Chat,Order
from .utils import agent_find_data
from .gpt import agent_find_data_gpt,detct_question,health_edu_question
from django.utils import timezone
from django.http import JsonResponse
from django.contrib import messages
from .forms import ResetPasswordForm
from django.contrib.auth.hashers import make_password
import threading
import cv2
from django.http import StreamingHttpResponse
from django.shortcuts import render
import numpy as np

import cv2
import threading
import time
import queue
import pyttsx3
from django.http import StreamingHttpResponse
from django.shortcuts import render

import json
# Create your views here.

# 登入頁面處理函數
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            # 嘗試根據 username 找到使用者
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 如果找不到該用戶，發送錯誤訊息
            messages.error(request, 'Username does not exist')
            return render(request, 'login.html')

        # 使用 authenticate 驗證用戶名和密碼
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # 登錄成功
            login(request, user)
            try:
                # 嘗試獲取 Profile 並檢查 patient_id
                profile = Profile.objects.get(user=user)
                patient_id = profile.patient_id
                
                print(f"Patient ID: {patient_id}")  # 可以做進一步處理
                messages.success(request, 'User Logged in Successfully')
                return redirect('chat_api')  # 重定向到指定頁面
            except Profile.DoesNotExist:
                # 如果 Profile 不存在，發送錯誤訊息並重定向
                messages.error(request, 'No profile associated with this account')
                return redirect('login')
        else:
            # 驗證失敗，發送錯誤訊息
            messages.error(request, 'Invalid username or password')

    # GET 請求時渲染登錄頁面
    return render(request, 'login.html')

# 登出頁面處理函數
def logout(request):
    return render(request, 'login.html')

# 醫院首頁處理函數
def hospital_home(request):
     return render(request,'home.html')

# 全局攝影機資源管理
camera = None
camera_lock = threading.Lock()

# 獲取攝影機資源的函數
def get_camera():
    global camera
    with camera_lock:
        if camera is None or not camera.isOpened():
            try:
                camera = cv2.VideoCapture(0)
                #camera = cv2.VideoCapture("http://localhost:8081/video")
                if not camera.isOpened():
                    print("無法開啟攝影機")
                    return None
            except Exception as e:
                print(f"攝影機初始化錯誤: {e}")
                return None
        return camera

# 載入人臉辨識模型
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# 語音播放函數
def text_to_speech_engine(text):
    def speak():
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    
    speech_thread = threading.Thread(target=speak)
    speech_thread.start()

# 全局問候狀態變量
greeting_status = {
    'can_greet': True,
    'last_greet_time': 0
}
chat_api_last_seen = {
    'last_seen_time': time.time()
}
danger_status_lock = threading.Lock()
current_danger_status = False

# 偵測人臉，並播放語音
def detect_faces(frame, enable_detection=True,current_page='home',request=None):
    """偵測人臉，並播放語音"""
    global current_danger_status
    #last_seen_time = time.time()
    if not enable_detection:
        return frame
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    current_time = time.time()
  
    if len(faces) > 0:
        #print("偵測到人！")
        if current_page == 'chat_api':
            chat_api_last_seen['last_seen_time'] = current_time
        if current_page == 'home':
            if greeting_status['can_greet'] and (current_time - greeting_status['last_greet_time']) >= 40:
                print("播放歡迎語音")
                text_to_speech_engine("歡迎使用血液透析智能問答")
                greeting_status['can_greet'] = False
                greeting_status['last_greet_time'] = current_time
    else:
        #print("沒有偵測到人")
        if current_page == 'chat_api':
                    if time.time() - chat_api_last_seen['last_seen_time'] > 5:
                        #print("⚠️ 危險：5 秒未偵測到人臉")
                        danger_triggered = True
                        #chat_api_last_seen['last_seen_time']= time.time()
                        with danger_status_lock:
                            current_danger_status = True
                        
                    else:
                        with danger_status_lock:
                            current_danger_status = False
        greeting_status['can_greet'] = True
    
    # 在畫面上標示人臉
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
    
    return frame

# 產生影像串流（MJPEG 格式）
def generate_frames(request):
    """產生影像串流（MJPEG 格式）"""
    last_seen_time = time.time()
    current_page = request.session.get('current_page', 'home')
    while True:
        cam = get_camera()
        if cam is None:
            # 無法獲取攝影機時回傳空白或錯誤影像
            frame = np.zeros((480, 640, 3), np.uint8)
            cv2.putText(frame, "Camera unavailable", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(1)
            continue

        success, frame = cam.read()
        if not success:
            print("無法讀取攝影機畫面")
            # 嘗試釋放並重新獲取攝影機
            with camera_lock:
                if camera is not None:
                    camera.release()
                    camera = None
            continue
        
        # 檢查是否啟用人臉偵測
        enable_detection = request.session.get('face_detect_active', False)
        #current_page = request.session.get('current_page', 'home')
        if enable_detection:
            frame = detect_faces(frame, enable_detection, current_page,request=request)
        
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# 提供 MJPEG 影像串流
def camera_feed(request):
    """提供 MJPEG 影像串流"""
    return StreamingHttpResponse(generate_frames(request), content_type="multipart/x-mixed-replace; boundary=frame")

# 訪問 Home 頁面時啟動人臉偵測
def home(request):
    """訪問 Home 頁面時啟動人臉偵測"""
    request.session['current_page'] = 'home'
    request.session['face_detect_active'] = True
    # 確保攝影機已初始化
    get_camera()
    return render(request, 'home.html')

# 停止人臉偵測但不釋放攝影機資源
def stop_face_detection(request):
    """停止人臉偵測但不釋放攝影機資源"""
    request.session['face_detect_active'] = False
    print("停止人臉偵測")
    return JsonResponse({'status': 'success'})

# 完全釋放攝影機資源
def release_camera(request):
    """完全釋放攝影機資源"""
    global camera
    with camera_lock:
        if camera is not None:
            camera.release()
            camera = None
    print("攝影機資源已釋放")
    return JsonResponse({'status': 'success'})
# Django 伺服器關閉時結束語音執行緒
import atexit

# 關於我們頁面處理函數
def about_us(request):
    return render(request, 'about-us.html') 

# 重設密碼頁面處理函數
def reset_password(request):
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            patient_id = form.cleaned_data['patient_id']
            new_password = form.cleaned_data['new_password']

            try:
                # 查找用戶及對應的 Profile
                user = User.objects.get(username=username)
                profile = Profile.objects.get(user=user)

                # 驗證 patient_id 是否匹配
                if profile.patient_id == patient_id:
                    # 更新密碼
                    user.password = make_password(new_password)
                    user.save()
                    messages.success(request, "Password reset successfully. You can now log in.")
                    return redirect('login')  # 重定向到登入頁面
                else:
                    messages.error(request, "Patient ID does not match for the given username.")
            except (User.DoesNotExist, Profile.DoesNotExist):
                messages.error(request, "Invalid Username or Patient ID.")
    else:
        form = ResetPasswordForm()

    return render(request, 'reset_password.html', {'form': form})

# 獲取危險狀態
def get_danger_status(request):
    global current_danger_status
    with danger_status_lock:
        status = current_danger_status
    
    print("danger_status is ",status)
    return JsonResponse({'danger': status})

# 聊天 API 處理函數
def chat_api(request):
    request.session['face_detect_active'] = True
    request.session['current_page'] = 'chat_api'
    request.session['danger_status'] = False
    # 確保攝影機已初始化
    get_camera()
    
    try:    
        profile = Profile.objects.get(user=request.user)
        patient_id = profile.patient_id  # 這是我們要傳遞的 patient_id
        print(f"Patient ID in chatbot: {patient_id}")  # For debugging
    except Profile.DoesNotExist:
        patient_id = None 

    # 處理 GET 請求中的清除操作
    if request.method == 'GET' and request.GET.get('clear') == 'true':
        Chat.objects.filter(user=request.user).delete()

    chats = Chat.objects.filter(user=request.user)

    # 處理 POST 請求
    if request.method == 'POST':
        print("POST request received")  # 確認 POST 請求進來了

        # 確保 message 參數存在
        data = json.loads(request.body)
        question = data.get('message')
        print(f"Received message: {question}")
        if question:
            detect = detct_question(question)
            print(f"detct_question: {detect}")  # 確認提取的訊息是有效的
            if detect == 1:
                current_time = timezone.now()
                print("reponse2..")
                response2 = agent_find_data_gpt(question, patient_id, current_time)
                print("reponse2 is ",response2)

                # 儲存訊息與回應
                if response2:  # 確保 response 是有效的
                    chat = Chat(user=request.user, message=question, response=response2, created_at=timezone.now())
                    chat.save()
                    print("Chat saved!")  # 確認 chat 是否儲存成功
                else:
                    print("No response generated to save!")  # 沒有回應時的提示
            elif detect == 2:
                response2 = health_edu_question(question)
            else:
                response2 = "請詢問醫護人員"
            
            return JsonResponse({
                'message': question,
                'response': response2,
                'category': detect,
                'dangerous': False
            })
        else:
            print("Invalid question, no response generated")  # 沒有訊息，無法處理

    # 渲染聊天頁面
    print("return")
    danger_status = request.session.get('danger_status', False)
    print("danger_status is ", danger_status)
    return render(request, 'chat_api.html', {
        'chats': chats,
        'patient_id': patient_id,
        'danger_status': danger_status,
        'category': 0
    })
    
# 聊天機器人頁面處理函數
def chatbot(request):
    request.session['face_detect_active'] = True
    request.session['current_page'] = 'chatbot'
    request.session['danger_status'] = False
    # 確保攝影機已初始化
    # get_camera()
    
    try:    
        profile = Profile.objects.get(user=request.user)
        patient_id = profile.patient_id  # 這是我們要傳遞的 patient_id
        print(f"Patient ID in chatbot: {patient_id}")  # For debugging
    except Profile.DoesNotExist:
        patient_id = None 

    # 處理 GET 請求中的清除操作
    if request.method == 'GET' and request.GET.get('clear') == 'true':
        Chat.objects.filter(user=request.user).delete()

    chats = Chat.objects.filter(user=request.user)

    # 處理 POST 請求
    if request.method == 'POST':
        print("POST request received")  # 確認 POST 請求進來了

        # 確保 message 參數存在
        data = json.loads(request.body)
        question = data.get('message')
        print(f"Received message: {question}")
        if question:
            detect = detct_question(question)
            print(f"detct_question: {detect}")  # 確認提取的訊息是有效的
            if detect == 1:
                current_time = timezone.now()
                print("reponse2..")
                response2 = agent_find_data_gpt(question, patient_id, current_time)
                print("reponse2 is ",response2)

                # 儲存訊息與回應
                if response2:  # 確保 response 是有效的
                    chat = Chat(user=request.user, message=question, response=response2, created_at=timezone.now())
                    chat.save()
                    print("Chat saved!")  # 確認 chat 是否儲存成功
                else:
                    print("No response generated to save!")  # 沒有回應時的提示
            elif detect == 2:
                response2 = health_edu_question(question)
            else:
                response2 = "請詢問醫護人員"
            
            return JsonResponse({
                'message': question,
                'response': response2,
                'category': detect,
                'dangerous': False
            })
        else:
            print("Invalid question, no response generated")  # 沒有訊息，無法處理

    # 渲染聊天頁面
    print("return")
    return render(request, 'chatbot.html', {'chats': chats, 'patient_id': patient_id})

from asgiref.sync import sync_to_async

# 病患註冊頁面處理函數
def patient_register(request):
    if request.method == 'POST':
        form = CreationUser(request.POST)  # 將提交的數據傳入表單
        if form.is_valid():
            form.save()  # 保存新用戶
            return redirect('login')  # 跳轉到登錄頁面
        else:
            print(form.errors)  # 輸出錯誤信息以便調試
    else:
        form = CreationUser()  # 初始化空表單

    # 傳遞表單到模板
    return render(request, 'patient-register.html', {'form': form})