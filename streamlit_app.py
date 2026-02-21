import pandas as pd 
import streamlit as st
import os
from datetime import datetime, timedelta
import plotly.express as px
import json

# case 1 : gspread 사용
# from googleapiclient.discovery import build
# from oauth2client.service_account import ServiceAccountCredentials
# import gspread
# scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
# json_key_path = 'auth/avian-buffer-452112-j1-b7babadd0268.json'
# credential = ServiceAccountCredentials.from_json_keyfile_name(json_key_path,scope)
# gc = gspread.authorize(credential)
# spreadsheet_url = "https://docs.google.com/spreadsheets/d/1QRdgLOJP6sR1bqdg4qDORy_il3UHyIb0NE93UlK9-Ow/edit?gid=0#gid=0"
# doc = gc.open_by_url(spreadsheet_url)
# sheet = doc.worksheet("시트1")
# df = pd.DataFrame(sheet.get_all_values())
# st.write(df)

# case 2 : google-api-python-client 사용
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.service_account import Credentials

page_css = '''
<style>
@font-face {
    font-family: 'GMarketSans';
    src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/noonfonts_2001@1.1/GmarketSansLight.woff') format('woff');
    font-weight: 300;
    font-display: swap;
}

@font-face {
    font-family: 'GMarketSans';
    src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/noonfonts_2001@1.1/GmarketSansMedium.woff') format('woff');
    font-weight: 500;
    font-display: swap;
}

@font-face {
    font-family: 'GMarketSans';
    src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/noonfonts_2001@1.1/GmarketSansBold.woff') format('woff');
    font-weight: 700;
    font-display: swap;
}
/* 전체 앱에 폰트 적용 */
*, .stApp{
  font-family: 'GMarketSans';
  
}
.stMainBlockContainer {
  margin-top: 30px;
  padding: 50px;
}


</style>
'''

st.set_page_config(layout='wide')
st.html(page_css)

# 연결하려는 시트ID
SPREADSHEET_ID  = '1QRdgLOJP6sR1bqdg4qDORy_il3UHyIb0NE93UlK9-Ow'

# 인증서 확인 (구글 로그인 - 사용자추가로 사용하는 방법)
# def get_creds():
#   creds = None

#   # 이미 인증서가 있는 경우,
#   if os.path.exists("token.json"):
#     creds = Credentials.from_authorized_user_file("token.json", SCOPES)
#     st.write(f"저장된 token 파일 읽기 성공 - 만료일자 {creds.expiry}")
#     # st.write(f"만료까지 남은시간 : {creds.expiry - datetime.now()}")

#   # 유효한 자격인증서 없는 경우, 로그인 (신규사용자)
#   if not creds or not creds.valid:
#     if creds and creds.expired and creds.refresh_token:
#       creds.refresh(Request())
#     else:
#       flow = InstalledAppFlow.from_client_secrets_file("token.json", SCOPES)
#       creds = flow.run_local_server(port=0)
#     # Save the credentials for the next run
#     with open("token.json", "w") as token:
#       token.write(creds.to_json())

#   return creds

css = """
<style>
.main {
  background-color: #f8fafc;
}
.stButton>button {
  width: 100%;
  border-radius: 10px;
  background-color: #2563eb;
  color: white;
}
.card {
  background-color: white;
  padding: 20px;
  border-radius: 15px;
  border: 1px solid #f1f5f9;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  margin-bottom: 20px;
}
.metric-title {
  font-size: 0.8rem;
  color: #94a3b8;
  margin-bottom: 5px;
}
.metric-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: #1e293b;
}
.sidebar-title {
  font-size: 1.3rem;
  font-weight: bold;
  margin-bottom: 10px;
}
</style>
"""
st.html(css)


class SheetManager:
  def __init__(self, spreadsheet_id): #"auth/credentials.json" credentials_file=(st.secrets["creds"])
    self.spreadsheet_id = spreadsheet_id
    # self.creds_file = credentials_file
    self.service = None
    self._connect()

  def _connect(self):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    creds_info = json.loads(st.secrets["creds"])

    # self.creds = Credentials.from_service_account_file(self.creds_file, scopes=SCOPES)
    self.creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    self.service = build("sheets","V4",credentials=self.creds,static_discovery=False)

  def read(self, sheet_name="시트1", range_str="B2:F300"):
    try:
      result = self.service.spreadsheets().values().get(
        spreadsheetId = self.spreadsheet_id,
        range = f"{sheet_name}!{range_str}",
        valueRenderOption = "UNFORMATTED_VALUE",
        dateTimeRenderOption = "FORMATTED_STRING"
      ).execute()

      rows = result.get("values",[])
      if not rows:
        return pd.DataFrame()
      
      df = pd.DataFrame(rows[1:],columns=rows[0])
      return df
    
    except HttpError as e:
      st.error(f"읽기 오류 : {e}")
      return pd.DataFrame()
  
  def append(self, data, sheet_name="시트1"):
    try:
      result = self.service.spreadsheets().values().append(
        spreadsheetId = self.spreadsheet_id,
        range = sheet_name,
        valueInputOption = "RAW",
        insertDataOption = "INSERT_ROWS",
        body = {"values" : [data]}
      ).execute()

      updates = result.get('updates',{})
      new_range= updates['updatedRange'] # 신규 추가된 row

      if updates:
        st.success(f"✅{updates['updatedRows']} 행 추가됨")
        return updates['updatedRange']
      return None
      
    except HttpError as e:
      st.error(f"추가 오류 : {e}")
      return None

if "user_id" not in st.session_state:
  st.session_state.user_id = None

# --- 사이드바 (로그인 및 네비게이션) ---
with st.sidebar:
  st.html('<p class="sidebar-title">🏦 대출 관리자</p>')
  if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

  if not st.session_state.logged_in:
    st.subheader("로그인")
    password = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("로그인"):
      if password == "1134":
        st.session_state.logged_in = True
        st.rerun()
      else:
        st.error("비밀번호가 틀렸습니다.")

  else:
    st.success("인증 완료")
    
    # selected_name = st.radio("목록", list(LOAN_DATA.keys()), label_visibility="collapsed")
    
    if st.button("로그아웃"):
      st.session_state.logged_in = False
      st.rerun()

# --- 메인 화면 콘텐츠 ---
if st.session_state.get('logged_in'):

  if 'sheet_manager' not in st.session_state:
    st.session_state.sheet_manager = SheetManager(SPREADSHEET_ID)

  manager = st.session_state.sheet_manager
  df = manager.read(sheet_name="시트1" ,range_str="B2:F300")
  df = df.dropna(subset=['Date'])
  df['month'] = pd.to_datetime(df['Date']).dt.month
  currency_cols = ['상환금액','원금','이자']
  df[currency_cols] = df[currency_cols].replace('','0').astype(int)

  
  data = manager.read(sheet_name="시트1" ,range_str="I2:L300")
  full_list = df['대출명'].unique().tolist()
  except_list = df.loc[df['원금'] ==0, "대출명"].unique().tolist()
  loan_list = [item for item in full_list if item not in except_list]

  df = df.loc[df["대출명"].isin(loan_list)]
  

  with st.sidebar:
    st.markdown("---")
    st.caption("대출 목록 선택")
    loan_name = st.radio("목록", loan_list, label_visibility="collapsed")

  data = data.loc[data["대출명"] == loan_name].iloc[0]
  df = df.loc[df["대출명"] == loan_name]

  cols = st.columns((2,2))

  with cols[0]:
    st.title(f"{loan_name} 현황")
    st.write("대출 만기일까지의 상환 추이 및 내역을 확인하세요.")

  with cols[1]:
    st.html(f"""
      <div style="display: flex; gap: 10px; margin-top: 20px;">
        <div class="card" style="flex: 1; padding: 10px; text-align: center;">
          <div class="metric-title">이자율</div>
          <div class="metric-value" style="color: #2563eb;">{data['이자율']*100:.2f}%</div>
        </div>
        <div class="card" style="flex: 1; padding: 10px; text-align: center;">
          <div class="metric-title">기간</div>
          <div class="metric-value">{data['대출기간']}</div>
        </div>
      </div>
    """)

  with cols[1].container(border=True):
    st.html('<b>📉 상환 잔액 변동 추이</b>')
    # fig_line = px.area(df, x='Date', y='원금', color_discrete_sequence=['#3b82f6'])
    # fig_line.update_layout(
    #     margin=dict(l=0, r=0, t=20, b=0),
    #     height=300,
    #     xaxis_title=None,
    #     yaxis_title=None,
    #     paper_bgcolor='rgba(0,0,0,0)',
    #     plot_bgcolor='rgba(0,0,0,0)'
    # )
    # st.plotly_chart(fig_line, width='stretch')
    # st.html('</div>')
    today = datetime.now()
    prev_date = today - timedelta(days=60)
    next_date = today + timedelta(days=60)
    fig = px.line(df, 
              x='Date', 
              y=['원금'], 
              color='대출명', 
              markers=True,)
              # title="대출별 상환금액 추이")
    fig.update_traces(connectgaps=True, line_shape="hv")
    fig.update_layout(xaxis=dict(range=[prev_date, next_date]),yaxis=dict(range=[0, df['원금'].max()*1.2]))
    st.plotly_chart(fig)


  with cols[0]:
    df_styled = df.style.format({
      '상환금액': '{:,.0f}원',
      '이자': '{:,.0f}원', 
      '원금': '{:,.0f}원'
      })
    with st.expander("상세보기", expanded=True):
      st.dataframe(df_styled,hide_index=True)

  
  with cols[0]:
    # 데이터 추가 
    sub_cols = st.columns(3)
    date_input = sub_cols[0].date_input(label="입금날짜", value='today')  
    principal = sub_cols[1].number_input(label="잔여원금", value=df['원금'].min(), disabled=True)
    
    sub_cols = st.columns(3)
    repayment = sub_cols[0].number_input(label='상환금액',value=0)
    interest = sub_cols[1].number_input(label='이자',value=0)
    
    new_row = {"Date":date_input, "대출명":loan_name, "상환금액":repayment, "이자":interest, "원금":principal-repayment}
    new_row["Date"] = new_row["Date"].strftime("%Y-%m-%d")
    new_row_list = list(new_row.values())

    if st.button("업데이트"):
      st.write(new_row_list)
      manager.append(new_row_list)
