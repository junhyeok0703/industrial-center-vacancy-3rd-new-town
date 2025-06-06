from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import json
from datetime import datetime

class NaverLandScraper:
    def __init__(self):
        self.options = webdriver.ChromeOptions()
        # self.options.add_argument('--headless')  # 테스트시에는 주석처리
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=self.options)
        self.driver.implicitly_wait(5)
    
    def scroll_to_bottom(self):
        """페이지를 끝까지 스크롤하면서 모든 매물을 로드"""
        print("\n모든 매물 로딩 중...")
        last_height = 0
        no_new_scrolls = 0
        
        scroll_area = self.driver.find_element(By.CLASS_NAME, 'item_list--article')

        while no_new_scrolls < 3:
            current_height = self.driver.execute_script("return arguments[0].scrollHeight", scroll_area)
            
            if current_height == last_height:
                no_new_scrolls += 1
            else:
                no_new_scrolls = 0
                print("스크롤 중...")
            
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_area)
            time.sleep(1)
            
            last_height = current_height
        
        print("모든 매물 로딩 완료!")
        
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)
    
    def scrape_items(self, url, target_count=1000):
        """메인 크롤링 로직"""
        all_items = []  # 최종 결과 저장 리스트
        try:
            print(f"\n크롤링 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.driver.get(url)

            # 페이지가 완전히 로드될 시간을 잠시 대기
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.item_inner"))
            )

            # 1) 모든 매물을 끝까지 스크롤해서 로드
            self.scroll_to_bottom()

            # 2) 모든 매물 요소를 한 번에 가져오기
            items = self.driver.find_elements(By.CSS_SELECTOR, "div.item_inner")
            total_items = len(items)
            print(f"\n총 {total_items}개의 매물을 발견했습니다. 데이터를 수집합니다.")

            # 3) 각 매물을 순회하며 클릭 -> 상세정보 수집
            for index in range(total_items):
                # 동적 페이지 특성상 재탐색
                items = self.driver.find_elements(By.CSS_SELECTOR, "div.item_inner")
                if index >= len(items):
                    # 혹시나 스크롤 과정에서 매물 수집이 달라지면 안전장치
                    break

                item = items[index]

                try:
                    # (a) 클릭 전에 해당 매물을 뷰포트 중앙쯤으로 이동
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", 
                        item
                    )
                    time.sleep(0.5)

                    # (b) 클릭 가능 상태가 될 때까지 대기 (intercept 방지)
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable(item)
                    )

                    # (c) 매물 클릭
                    item.click()
                    time.sleep(1)  # 상세 정보가 뜨도록 잠시 대기
                    print(f"[{index+1}/{total_items}] 매물 클릭 완료")

                    # (d) 상세 정보 패널에서 건물명(센터명칭) 파싱
                    building_name = "정보없음"
                    try:
                        detail_panel = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located(
                                (By.CLASS_NAME, "detail_panel")
                            )
                        )
                        building_element = detail_panel.find_element(
                            By.CLASS_NAME, "architecture_item_text"
                        )
                        building_name = building_element.text.strip()
                    except NoSuchElementException:
                        print("건물명을 찾을 수 없습니다.")
                    except TimeoutException:
                        print("상세 패널 로드가 늦어 건물명 추출 실패")

                    # (e) 리스트 뷰 정보 파싱
                    name_text = item.find_element(By.CSS_SELECTOR, "span.text").text
                    price_text = item.find_element(By.CSS_SELECTOR, "span.price").text
                    if self.element_exists(item, By.CSS_SELECTOR, "span.spec"):
                        spec_text = item.find_element(By.CSS_SELECTOR, "span.spec").text
                    else:
                        spec_text = "정보없음"

                    item_data = {
                        '이름': name_text,
                        '가격': price_text,
                        '면적 및 층수': spec_text,
                        '센터명칭': building_name
                    }

                    print(f"   → {item_data['이름']} | {item_data['가격']} | {item_data['면적 및 층수']} | {item_data['센터명칭']}")
                    all_items.append(item_data)

                    # (f) 500개마다 중간 저장
                    if len(all_items) % 500 == 0:
                        self.save_to_json(all_items)
                        print(f"   → 중간 저장 완료: 현재 {len(all_items)}개")

                except StaleElementReferenceException:
                    print(f"[{index+1}/{total_items}] StaleElementReference 발생 - 다음으로 넘어감")
                    continue
                except Exception as e:
                    print(f"[{index+1}/{total_items}] 오류 발생: {e}")
                    continue

                # 목표 갯수에 도달하면 중단
                if len(all_items) >= target_count:
                    print(f"\n목표 수집 개수({target_count}개)에 도달했습니다.")
                    break

            # 4) 전체 결과 최종 저장
            self.save_to_json(all_items)
            return all_items

        except Exception as e:
            print(f"\n크롤링 중 오류 발생: {e}")
            return all_items

        finally:
            print(f"\n크롤링 종료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.driver.quit()
    
    def element_exists(self, parent, by, value):
        try:
            parent.find_element(by, value)
            return True
        except NoSuchElementException:
            return False
    
    def save_to_json(self, data, filename=None):
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"네이버_매물데이터_의왕시_포일동_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, ensure_ascii=False, indent=2, fp=f)

def main():

    url = 'https://new.land.naver.com/offices?ms=37.3974469,126.9894785,16&a=APTHGJ&e=RETAIL' # 의왕 포일동
    scraper = NaverLandScraper()
    
    print("네이버 부동산 크롤링을 시작합니다...")
    items = scraper.scrape_items(url, target_count=1000)
    
    if items:
        scraper.save_to_json(items)
        print(f"\n크롤링 완료! 총 {len(items)}개의 매물 수집")
    else:
        print("\n수집된 매물이 없습니다.")

if __name__ == "__main__":
    main()
