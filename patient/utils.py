import json
from ollama import Client
import pandas as pd
from gtts import gTTS
import os
import re
import pyttsx3,time
from langchain_ollama import ChatOllama
import threading
import pyttsx3
excel_file_path = r'C:\Users\lala\agent\revised_data.xlsx'
#excel_file_path = '/app/revised_data.xlsx'

  # Replace with your Excel file path

# Read the column names from the Excel file
df = pd.read_excel(excel_file_path)
keywords = list(df.columns)  # Extract the column names as a list
# Initialize the Ollama client with the specified host




#client = Client(host='http://192.168.63.179:11434')
llm = ChatOllama(
    model="llama3.1:8b",  # 使用的模型名稱
    base_url="http://140.116.247.169:11434",  # 新的 IP 地址
    temperature=0  # 設置 temperature 為 0，確保輸出穩定
)

def check_question_is_related(question, keywords):
    # Join the measurement keywords into a string
    keywords_str = ", ".join(keywords)
    
    prompt = f"""
        你是醫療服務助手。
        根據病患的問題，請判斷{question}的內容是否在詢問血液透析報告相關問題
        血液透析報告的內容中紀錄的項目為{keywords_str}
        僅輸出 `True` 或 `False`，不要包含其他內容。只需直接回答，保持格式正確，且不解釋理由。
        問題:請問我的血壓狀況
        回答:True
        問題:請問醫生有女朋友嗎
        回答:False
        問題:請問透析結束體重
        回答:True
        問題:請問負責我的護士是哪位
        回答:False
        問題:請問我的眼睛顏色
        回答:False
    """
    response = llm.invoke(prompt)  # 使用 llm.predict 來獲取回應
    
    # 使用正則表達式提取 True 或 False
    match = re.search(r'\b(True|False)\b', response)
    if match:
        return match.group(0) == "True"
    else:
        raise ValueError(f"Unexpected output from model: {response}")

def extract_col_name(question, keywords):
    # Join the measurement keywords into a string
    keywords_str = ", ".join(keywords)
    
    prompt = f"""
        你是醫療服務助手。
        根據病患的問題，自行判斷並提取最相關的資料名稱，從以下清單中選取：{keywords_str}。
        問題：{question}

        請注意以下指導：
        1. 若問題涉及血壓，請返回「血壓收縮」和「血壓舒張」。
        2. 若問題涉及血壓，且有寫透析前後則回傳「透析前舒張壓」和「透析前收縮壓」。
        3. 若與「透析液離子」相關返回「透析液Ca」和「透析液Na」。
        4. 若與地點位置相關，返回「透析床號」和「透析機編號」。
        5. 若無法匹配以上規則，返回「無資料」。
        6.若問題非常明確（如只詢問「預估脫水量」），請僅回傳「預估脫水量」。
        
        如果問題無法與以上資料名稱匹配，請返回「無資料」。
        
        回傳格式，請不要額外增添其他回應。
        請只返回符合條件的資料名稱，以逗號分隔，例如：透析床號, 透析機編號。
        如果沒有資料，請返回「請」。
    """
    #response = llm.invoke(prompt)  # 使用 llm.predict 來獲取回應
    #print("response ",response)
    response = llm.invoke(prompt).content.strip()
    if response == "無資料":
        return "無資料"
    # 使用正則表達式提取資料名稱
    valid_keywords = [keyword for keyword in keywords if keyword in response]
    
    if not valid_keywords:
        return "無資料"
    
    return ", ".join(valid_keywords)

    # # Call Ollama API to get the response
    # response = client.chat(
    #     model='llama3.1:8b-instruct-fp16',
    #     messages=[
    #         {"role": "user", "content": prompt}
    #     ]
    # )

    # # Extract the assistant's content
    # assistant_content = response.get('message', {}).get('content', "").strip()

    # # Check if the returned content contains any valid keyword
    # valid_keywords = [keyword for keyword in keywords if keyword in assistant_content]

    # if not valid_keywords:  # If no valid keywords were found, return "無資料"
    #     return "和血液透析報告無關"
    
    # return {"詢問的醫療資訊": valid_keywords}

def find_patient_data(query_data, df):
    """根據病歷號碼查詢病患的姓名、年齡、性別，並返回客製化問候語與醫療資訊。"""

    病歷號碼 = str(query_data.get('病歷號碼')).strip()  # 確保病歷號碼為字串
    詢問的醫療資訊 = query_data.get('詢問的醫療資訊', [])  # 查詢的醫療資訊
    目前時間 = query_data.get('目前時間')  # 查詢的時間 (datetime 類型)

    if not 病歷號碼 or not 詢問的醫療資訊 or not 目前時間:
        return "請提供完整的查詢條件（病歷號碼、目前時間、詢問的醫療資訊）"

    # 根據病歷號碼篩選
    filtered_df = df[df['病歷號碼'].astype(str).str.strip() == 病歷號碼]

    if filtered_df.empty:
        return f"無此病歷號碼 {病歷號碼} 的資料"

    # 確保 `目前時間` 是無時區的時間
    目前時間 = 目前時間.replace(tzinfo=None)

    # 找出最接近的時間
    filtered_df['目前時間'] = pd.to_datetime(filtered_df['目前時間']).dt.tz_localize(None)
    filtered_df['時間差'] = filtered_df['目前時間'].apply(lambda x: abs(x - 目前時間))
    closest_record = filtered_df.loc[filtered_df['時間差'].idxmin()]

    # 提取病患資訊
    name = closest_record.get('姓名', '未知')
    age = closest_record.get('年齡', '未知')
    gender = closest_record.get('性别', '未知')

    # 處理醫療資訊查詢
    medical_info_list = [info.strip() for info in 詢問的醫療資訊]
    existing_columns = [col for col in medical_info_list if col in closest_record.index]

    if not existing_columns:
        return f"您查詢的醫療資訊欄位不存在於資料中"

    # 提取醫療資訊
    medical_data = {col: closest_record[col] for col in existing_columns}
    medical_info_str = ', '.join([f"{key}: {value}" for key, value in medical_data.items()])

    # 返回結果
    result = (
        f"病患 {name}（年齡: {age}, 性別: {gender}）在時間 {closest_record['目前時間']} "
        f"的醫療資訊為：{medical_info_str}"
    )

    return result

def retrieve_common_data(question, common_data_ranges):
    """根據問題檢索常見醫療資訊"""
    for key, info in common_data_ranges.items():
        if key in question:
            return f"{key}的正常範圍是{info['範圍']}。{info['描述']}"
    return "很抱歉，無法找到相關的醫療範圍資料。"

def get_closest_time(df, current_time, patient_id):
    """根據當前時間找出最接近的時間"""
    # 確保 '病歷號碼' 為字串，並移除前後空白字元
    df['病歷號碼'] = df['病歷號碼'].astype(str).str.strip()
    patient_id = str(patient_id)  # 確保 patient_id 是字串
    
    # 將 '目前時間' 轉為 datetime，並移除時區
    df['目前時間'] = pd.to_datetime(df['目前時間']).dt.tz_localize(None)
    
    # 確保 current_time 也是無時區的 datetime
    current_time = current_time.replace(tzinfo=None)
    
    # 篩選指定 patient_id 的資料
    filtered_df = df[df['病歷號碼'] == patient_id]
    
    # 如果篩選後的資料為空，返回 None
    if filtered_df.empty:
        print(f"沒有找到 patient_id {patient_id} 的資料")
        return None
    
    # 找出最接近的時間
    closest_time = min(filtered_df['目前時間'], key=lambda x: abs(x - current_time))
    
    print(f"對應 patient_id {patient_id} 最近的時間是 {closest_time}")
    return closest_time

def append_patient_info(data, patient_id, current_time):
    """
    確保傳入的 data 是字典，並追加病歷號碼和當前時間。
    """
    # 如果 data 不是字典，將其轉換為字典
    if not isinstance(data, dict):
        if isinstance(data, list):
            # 如果 data 是列表，轉換為 {"詢問的醫療資訊": data}
            data = {"詢問的醫療資訊": data}
        else:
            # 如果 data 是其他類型，轉換為空字典
            data = {}

    # 追加病歷號碼和目前時間
    updated_data = {
        **data,
        '病歷號碼': patient_id,
        '目前時間': current_time
    }
    #print("type ",type(updated_data))
    return updated_data

def generate_rag_response(patient_id,question, patient_data, data_range):

    """結合 LLM 生成回答"""
    # 將患者數據和常見資訊結合
    病歷號碼 = str(patient_id).strip()
    filtered_df = df[df['病歷號碼'].astype(str).str.strip() == 病歷號碼]

    # 提取病患資訊
    #filtered_df = df[df['病歷號碼'].astype(str).str.strip() == 病歷號碼]
    patient_info = filtered_df.iloc[0]  # 取出第一筆符合資料的病患資訊
    print("patient_onfo",patient_info)

    name = patient_info['姓名']
    age = patient_info['年齡']
    print("age",age)

    gender = patient_info['性别']

    print(patient_id,age,gender)
    context = f"患者的醫療數據：{patient_data}\n"
    prompt = f"""
    請協助回答病患對於醫生的提問
    你是一個醫療助手，根據以下資訊，回答患者的問題：
    {context}
    資料庫:{data_range}
    若{context}是和{data_range}相關則基於{data_range}知識生成結果
    若無關則回應{context}內容即可
    根據{age}{gender}加入稱謂
    問題：{question}
    
    請用自然語言生成一個清晰的回答。
    請生成關心病患的相關回應
    回答請簡短有力
    """
    # response = client.chat(
    #     model='llama3.1:8b-instruct-fp16',
    #     messages=[{"role": "user", "content": prompt}]
    # )
    
    # return response.get('message', {}).get('content', "").strip()
    response = llm.invoke(prompt).content.strip()  # 使用 `llm.predict` 代替 `client.chat`

    # 確保回應有效
    if not response or not isinstance(response, str):
        return "抱歉，我無法處理您的請求，請稍後再試。"

    return response.strip()

data_ranges = {
    "體溫": {"範圍": "36°C到37°C", "描述": "體溫應保持在36°C到37°C之間，過高或過低可能需要進一步檢查。"},
    "靜脈壓": {"範圍": "50-200 mmHg", "描述": "靜脈壓正常範圍為50-200 mmHg，過高或過低需注意血液流通情況。"},
    "脫水速率": {"範圍": "10-13ml/kg每小時", "描述": "脫水速率通常建議控制在每小時10-13ml/kg，例如60公斤患者約為每小時600-780ml。"},
    "透析液溫度": {"範圍": "36°C到37°C", "描述": "透析液溫度建議範圍為36°C到37°C，過高或過低可能影響治療效果。"},
    "血壓": {
        "範圍": "收縮壓90-140 mmHg，舒張壓60-90 mmHg",
        "描述": "血壓應維持在收縮壓90-140 mmHg與舒張壓60-90 mmHg之間，過高或過低可能影響透析安全性。"
    },
}



def text_to_speech_gtts(text, language='zh'):
    tts = gTTS(text=text, lang=language)  # 指定語言為中文
    audio_file = "response.mp3"  # 儲存語音檔案
    tts.save(audio_file)  # 保存音檔

    # 播放語音檔案
    os.system(f"start {audio_file}")  # Windows 播放
    # macOS 使用：os.system(f"afplay {audio_file}")
    # Linux 使用：os.system(f"mpg123 {audio_file}")

    return audio_file


def text_to_speech_engine(text):
    def speak():
        # while engine.isBusy():
        #     print("Busy")
        #     engine.stop()
        engine.say(text)
        engine.runAndWait()
        print("End !")
            #engine.endLoop()
            # engine.stop()  # 確保語音播放後能夠停止
        #     print("🔊 語音播放完成")
        # except Exception as e:
        #     print(f"❌ 發生錯誤: {e}")
        #     # if engine._inLoop:
        #     #     engine.endLoop()  # 確保播放結束後正確關閉 loop
        #     # print("🔊 語音播放完成")

    engine = pyttsx3.init()
    speak()
    # 使用多執行緒來執行語音合成
    # thread = threading.Thread(target=speak)
    # thread.start()
        
#     # def speak(text):
#     #     try:
#     #         with engine_lock:  # 確保同一時間只有一個線程能訪問語音引擎
#     #             engine.say(text)
#     #             if not engine.isBusy():  # 檢查語音引擎是否正在運行
#     #                 engine.runAndWait()
#     #     except RuntimeError as e:
#     #         print(f"Error in speech synthesis: {e}")
#     # 使用單獨的線程來執行語音播放
#     threading.Thread(target=speak).start()

def agent_find_data(question, patient_id, time):
    try:
        # Extract column name from the question
        result = extract_col_name(question, keywords)
        print("Extracted result:", result)
        print("type is ",type(result))
        if result != '和血液透析報告無關':
            # 提取詢問的醫療資訊
            #response = result.get("詢問的醫療資訊", [])
            response = result.split(", ")  
            print("Extracted medical information:", response)
            
            # Debug: 確認 '病歷號碼' 是否存在並進行清理
            df.columns = df.columns.str.strip()
            if '病歷號碼' not in df.columns:
                raise KeyError("'病歷號碼' 欄位不存在於 DataFrame 中，請檢查資料來源。")
            
            # 確保 '病歷號碼' 欄位數據處理正確
            df['病歷號碼'] = df['病歷號碼'].astype(str).str.strip()
            
            # 獲取最近的時間
            current_time = get_closest_time(df, time, patient_id)
            # print("Closest time:", current_time)
            
            # 拼接病患資訊
            complete_info = append_patient_info({"詢問的醫療資訊": response}, patient_id, current_time)
            # print("Complete patient info:", complete_info)
            
            # 查詢病患數據
            patient_data = find_patient_data(complete_info, df)
            # print("Retrieved patient data:", patient_data)
            
            # 使用生成模型生成最終回應
            final_response = generate_rag_response(patient_id, question, patient_data, data_ranges)
            print("Generated response:", final_response)
            
        else:
            final_response = result
            print("Final response (no relevant medical info):", final_response)
        
        warning_keywords = ['呼吸', '脈搏', '血壓收縮', '血壓舒張','體溫']
        if any(keyword in response for keyword in warning_keywords):
            final_response += " 若身體有任何不適，請立即告知醫護人員。"
        # 語音回應
        text_to_speech_engine(final_response)
        return final_response
    
    except Exception as e:
        # 捕捉並輸出所有例外
        print("An error occurred:   ", str(e))
        return f"Error: {str(e)}"

