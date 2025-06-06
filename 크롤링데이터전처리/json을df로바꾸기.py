import os
import pandas as pd
import json

# 원미구 폴더 경로
folder_path = '/Users/parkjunhyeok/콤파스_지식산업센터_공모전/크롤링/부천시_매물데이터/원미구'  # 폴더 경로를 실제 경로로 변경하세요
output_folder = '/Users/parkjunhyeok/콤파스_지식산업센터_공모전/크롤링데이터전처리/원미구'

# 모든 JSON 파일을 리스트로 불러오기
json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]

# 모든 JSON 파일을 DataFrame으로 변환 후 저장
for json_file in json_files:
    file_path = os.path.join(folder_path, json_file)
    
    # JSON 파일 로드
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # JSON 데이터를 DataFrame으로 변환
    df = pd.json_normalize(data)  # 데이터 구조에 따라 변환 방식이 달라질 수 있음
    
    # 저장할 경로 지정
    output_path = os.path.join(output_folder, json_file.replace('.json', '_output.csv'))
    
    # DataFrame을 CSV로 저장
    df.to_csv(output_path, index=False, encoding='utf-8')

    print(f"{json_file} -> {output_path} 저장 완료!")