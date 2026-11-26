# BÁO CÁO ĐÁNH GIÁ BENCHMARK RAG NHÓM 70% KHỐI HẠ TẦNG PHỔ THÔNG

> **Hệ thống**: `agent/knowledge_matcher.py` (`KnowledgeMatcher.search_by_mode`)  
> **Script thực nghiệm**: `benchmarks/benchmark_70_rag.py`  
> **Quy mô kho tri thức**: **643 mẫu** (`hardware_db.json`: 539 mẫu + `dataset_teacher_distilled.json` nạp trong RAM: 104 mẫu)  
> **Vector Backend thực thi**: `lsa_tfidf_svd (643, 96)` (pure-offline `TfidfVectorizer + TruncatedSVD`, 0% PyTorch, an toàn 4GB RAM)  
> **Ngày thực nghiệm**: 2026-11-26

---

## 1. Thiết Kế Bộ Đề Benchmark (28 Truy Vấn Né Từ Khóa / Tên Module)

Bộ kiểm thử gồm **28 truy vấn ngôn ngữ tự nhiên** (**14 Tiếng Việt + 14 Tiếng Anh**) bao phủ đầy đủ các họ vi mạch thuộc nhóm **70% khối hạ tầng phổ thông (Commodity Infrastructure)**:
- **Giao tiếp nối tiếp & Bus**: UART TX (`Q01`), UART RX (`Q02`), SPI Master (`Q03`), SPI Slave (`Q04`), I2C Bus (`Q05`), CRC-8 Generator (`Q28`).
- **Bộ đệm & Lưu trữ**: Synchronous FIFO (`Q06`), Asynchronous FIFO (`Q07`).
- **Bộ đếm & Định thời**: Gray Counter (`Q08`), BCD Counter (`Q09`), Up-Down Counter (`Q10`), Watchdog Timer (`Q24`), Frequency Divider (`Q25`), Edge/Pulse Detector (`Q26`), CDC Synchronizer (`Q27`).
- **FSM Điều khiển**: Traffic Light FSM (`Q11`), Vending Machine FSM (`Q12`), Digital Lock FSM (`Q13`), Button Debouncer (`Q23`).
- **Số học, Tín hiệu & Tổ hợp**: ALU (`Q14`), Multiplier (`Q15`), Divider (`Q16`), PWM Generator (`Q17`), Decoder 3-to-8 (`Q18`), BCD to 7-Segment (`Q19`), Priority Encoder (`Q20`), Universal Shift Register (`Q21`), SIPO Shift Register (`Q22`).

Tất cả 28 truy vấn đều được viết theo dạng **mô tả chức năng gián tiếp**, chủ động né tên module và từ khóa trực tiếp (kiểm tra tự động trong script xác nhận **0 rò rỉ tên module**).

---

## 2. Kết Quả Tổng Hợp So Sánh 3 Chế Độ (`keyword` vs `bm25` vs `hybrid`, kèm `vector` ablation)

Chạy `python benchmarks/benchmark_70_rag.py` (`top_k = 3`):

| Chế độ (Mode) | Recall@1 | Recall@3 | MRR@3 | Thời gian TB (ms/query) |
| :--- | :---: | :---: | :---: | :---: |
| `keyword` (cổ điển) | 15/28 (53.6%) | 18/28 (64.3%) | **0.5774** | 183.51 |
| `bm25` | 15/28 (53.6%) | **22/28 (78.6%)** | **0.6369** | 211.86 |
| `hybrid` (BM25 + 3-gram + Semantic Vector RRF) | **16/28 (57.1%)** | 21/28 (75.0%) | **0.6548** | 189.06 |
| `vector` (ablation thuần LSA SVD) | 11/28 (39.3%) | 18/28 (64.3%) | **0.4940** | 10.82 |

### Phân Tích Theo Ngôn Ngữ (14 Tiếng Việt vs 14 Tiếng Anh)

| Tập truy vấn | `keyword` (R@1 / R@3 / MRR) | `bm25` (R@1 / R@3 / MRR) | `hybrid` (R@1 / R@3 / MRR) | `vector` (R@1 / R@3 / MRR) |
| :--- | :---: | :---: | :---: | :---: |
| **Tiếng Việt (14)** | 11/14 / 11/14 / 0.786 | 10/14 / 11/14 / 0.738 | 8/14 / 11/14 / 0.667 | 6/14 / 8/14 / 0.476 |
| **Tiếng Anh (14)** | 4/14 / 7/14 / 0.369 | 5/14 / 11/14 / 0.536 | **8/14 / 10/14 / 0.643** | 5/14 / 10/14 / 0.512 |

---

## 3. Bảng Kết Quả Chi Tiết Từng Truy Vấn (Rank trong Top-3, `0` = Miss)

| ID | Lang | Họ Mạch (Family) | `keyword` | `bm25` | `hybrid` | `vector` | Hybrid Top-1 Trả Về |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| `Q01` | vi | UART TX | 1 | 1 | 1 | 3 | `uart_tx_8bit` |
| `Q02` | en | UART RX | 3 | 1 | 1 | 1 | `fsm_serialdata` |
| `Q03` | vi | SPI Master | 1 | 1 | 0 | 0 | `elevator_5floor_controller` |
| `Q04` | en | SPI Slave | 2 | 2 | 1 | 2 | `spi_slave_controller` |
| `Q05` | en | I2C Bus | 0 | 0 | 0 | 0 | `fsm_serialdata` |
| `Q06` | vi | Synchronous FIFO | 1 | 1 | 1 | 1 | `fifo_syn_8x8` |
| `Q07` | en | Asynchronous FIFO | 0 | 2 | 2 | 3 | `cvdp_agentic_queue_0001` |
| `Q08` | vi | Gray Counter | 0 | 0 | 0 | 0 | `binary_counter_4bit` |
| `Q09` | vi | BCD Counter | 0 | 3 | 1 | 1 | `bcd_counter_59` |
| `Q10` | en | Up-Down Counter | 3 | 1 | 1 | 3 | `up_down_counter` |
| `Q11` | vi | Traffic Light FSM | 1 | 1 | 3 | 0 | `microwave_timer_controller` |
| `Q12` | vi | Vending Machine FSM | 1 | 1 | 1 | 1 | `vending_machine` |
| `Q13` | en | Digital Lock FSM | 0 | 1 | 0 | 0 | `controller` |
| `Q14` | en | ALU | 1 | 0 | 1 | 1 | `alu_core` |
| `Q15` | vi | Multiplier | 1 | 0 | 1 | 3 | `multi_booth_8bit` |
| `Q16` | en | Divider | 1 | 1 | 1 | 1 | `div_16bit` |
| `Q17` | vi | PWM Generator | 1 | 1 | 2 | 1 | `fan_speed_controller` |
| `Q18` | vi | Decoder 3-to-8 | 0 | 0 | 0 | 0 | `programmable_delay_timer` |
| `Q19` | en | BCD to 7-Segment | 0 | 3 | 1 | 2 | `bcd_to_7seg_cathode` |
| `Q20` | en | Priority Encoder | 1 | 3 | 1 | 1 | `fixed_priority_arbiter` |
| `Q21` | vi | Universal Shift Register | 1 | 1 | 2 | 0 | `register_8bit_load` |
| `Q22` | en | SIPO Shift Register | 1 | 1 | 1 | 1 | `serial2parallel` |
| `Q23` | vi | Button Debouncer | 1 | 1 | 1 | 1 | `button_debouncer` |
| `Q24` | en | Watchdog Timer | 0 | 2 | 2 | 2 | `temperature_monitor_alarm` |
| `Q25` | vi | Frequency Divider | 1 | 1 | 1 | 0 | `freq_divider_1hz` |
| `Q26` | en | Edge / Pulse Detector | 0 | 3 | 0 | 0 | `serial2parallel` |
| `Q27` | vi | CDC Synchronizer | 1 | 1 | 1 | 1 | `dual_flop_sync` |
| `Q28` | en | CRC-8 Generator | 0 | 0 | 0 | 0 | `div_16bit` |

---

## 4. Nhận Xét Kỹ Thuật & Đề Xuất Cải Tiến Tiếp Theo

1. **Hiệu quả của `hybrid` RRF trên toàn cục và Tiếng Anh**:
   - Trên toàn bộ 28 truy vấn, `hybrid` đạt **MRR@3 cao nhất (0.6548)** và **Recall@1 cao nhất (57.1%)**, vượt `keyword` (+3.5% Recall@1, +10.7% Recall@3, +0.0774 MRR) và vượt `bm25` về độ chính xác Top-1 (+3.5% Recall@1, +0.0179 MRR).
   - Trên tập **14 truy vấn Tiếng Anh né từ khóa**, `hybrid` tăng vọt **Recall@1 từ 28.6% (`keyword`) / 35.7% (`bm25`) lên 57.1%** và **MRR từ 0.369 (`keyword`) lên 0.643** (+74.3% tương đối), chứng minh tác dụng cộng hưởng của nhánh Vector + 3-gram + BM25 RRF khi diễn đạt chức năng gián tiếp (ví dụ `Q04` SPI Slave, `Q19` BCD-to-7seg, `Q20` Priority Encoder lên hạng #1).
2. **Hạn chế quan sát được từ thực nghiệm (3 nguyên nhân gốc rễ)**:
   - **Kho dữ liệu I2C gốc còn mỏng (`Q05`)**: Mẫu I2C duy nhất trong DB hiện tại là `instruct60k_body` chỉ có spec 3 từ `"I2C module body"`, không có mô tả SCL/SDA/Start/Stop nên cả 4 chế độ đều miss khi câu hỏi né chữ `"I2C"`.
   - **Lệch miền ngôn ngữ giữa truy vấn và mẫu Teacher (`Q28`, `Q03`, `Q11`)**: Khi dùng backend offline `lsa_tfidf_svd` (96 chiều SVD), không gian TF-IDF không ánh xạ được đồng nghĩa xuyên ngôn ngữ (ví dụ câu hỏi Tiếng Anh `Q28` về CRC-8 không khớp với mẫu `crc8_generator` viết hoàn toàn bằng Tiếng Việt), đồng thời các từ khuôn mẫu Tiếng Việt lặp lại (như *"bộ điều khiển"*, *"tín hiệu"*) dễ gây nhiễu thứ hạng trong nhánh `vector` thuần (`Q03`, `Q11`, `Q21`).
   - **Thiếu từ đồng nghĩa khái niệm cho trường hợp né hoàn toàn (`Q08`, `Q18`)**: Khi câu hỏi mô tả Gray code hoặc Decoder 3-to-8 mà không chứa `"gray"` / `"giải mã"`, `lsa_tfidf_svd` chưa đủ năng lực suy luận ngữ nghĩa sâu như embedding đa ngôn ngữ (`fastembed` ONNX hoặc `gemini-embedding-001` cache `.npz`).
3. **Khuyến nghị**:
   - Sinh sẵn `knowledge_base/hardware_embeddings.npz` bằng `gemini-embedding-001` (hoặc cài `fastembed` đa ngôn ngữ) để nâng nhánh semantic cho cả truy vấn Tiếng Việt lẫn xuyên ngôn ngữ Anh–Việt.
   - Bổ sung mô tả chuẩn cho các mẫu có spec quá ngắn trong DB (như I2C controller) thông qua vòng lặp `save_verified_design` khi chạy thực tế.
