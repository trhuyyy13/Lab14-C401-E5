# Reflection - Lương Anh Tuấn

## 1. Đóng góp kỹ thuật và bằng chứng

### 1.1. Refactor benchmark pipeline
- Tách helper tổng hợp metric `_compute_summary` để tránh lặp logic tính toán và dễ mở rộng hệ thống metric.
- Thêm helper fallback `_default_failure_payload` trong runner để một test case lỗi không làm vỡ toàn bộ pipeline benchmark.
- Tách helper heuristic trong judge `_heuristic_scores` để luôn có chế độ dự phòng khi không gọi được OpenAI API.

Bằng chứng code:
- `main.py`: `_compute_summary`, `_is_hard_gate_pass`, ghi `reports/summary.json` và `reports/benchmark_results.json`.
- `engine/runner.py`: `_default_failure_payload`, `_build_result`, trạng thái pass/fail theo điểm judge.
- `engine/llm_judge.py`: dùng 2 judge model, có agreement và conflict resolution.

### 1.2. Đồng bộ luồng dữ liệu và script SDG/chunk
- Chuẩn hóa luồng tạo chunk trong `load_and_chunk_real_data(source_file)`.
- Cập nhật call-site in chunk list để khớp signature mới.
- Duy trì nguồn dữ liệu thống nhất theo `data.txt` trong script dataset/chunk.

Bằng chứng code:
- `data/synthetic_gen.py`: `def load_and_chunk_real_data(source_file: Path)`.
- `data/print_chunks.py`: gọi `load_and_chunk_real_data(repo / "data.txt")`.

### 1.3. Bằng chứng commit
- `12cebc79c86dfffd674b3e4ab2dfe788bb5eaaaf`: commit chính sửa các module `agent`, `engine`, `main.py`, `data/*.py`, `analysis/*`.
- `fcaddcda8b2b8e2c16291f948f02e773faeee658`: cập nhật kết quả benchmark và summary sau khi chạy lại với code mới.

## 2. Chiều sâu kỹ thuật đã áp dụng

### 2.1. Retrieval metrics
- Hit Rate: kiểm tra expected id có nằm trong top-k retrieved hay không (`calculate_hit_rate`).
- MRR: lấy nghịch đảo thứ hạng tài liệu đúng đầu tiên (`calculate_mrr`).
- Công thức: MRR = 1 / rank.

### 2.2. Multi-judge và độ đồng thuận
- Dùng 2 judge model (`gpt-4o-mini`, `gpt-4.1-mini`).
- Agreement rate được tính theo độ lệch điểm của 2 judge:
  `agreement = 1 - (abs(score_a - score_b) / 4)`.
- Nếu chênh lệch > 1 thì dùng `conflict_penalty` để giảm rủi ro optimistic bias.

### 2.3. Position bias
- Có kiểm tra position bias bằng `length_delta_ratio` trong `check_position_bias`.
- Ngưỡng cảnh báo bias: `delta > 0.6`.

Lưu ý học thuật:
- Hệ thống hiện tại chưa tính Cohen's Kappa. Đây là điểm cần bổ sung nếu muốn đẩy mạnh độ tin cậy phần đánh giá đa giám khảo.

## 3. Vấn đề gặp phải và cách giải quyết

### Vấn đề 1: Test case lỗi làm đứt pipeline
- Triệu chứng: một exception có thể phá vỡ luồng benchmark.
- Cách xử lý: bổ sung `_default_failure_payload` để trả payload an toàn, benchmark vẫn ghi report đầy đủ.

### Vấn đề 2: Mismatch signature hàm load chunk
- Triệu chứng: call-site script chunk/dataset sai tham số sau khi refactor.
- Cách xử lý: thống nhất API `load_and_chunk_real_data(source_file)` và cập nhật nơi gọi.

### Vấn đề 3: Đánh giá release cần rule rõ ràng
- Triệu chứng: khó quyết định release nếu chỉ nhìn một metric.
- Cách xử lý: dùng hard gate trong `main.py` với ngưỡng `hit_rate`, `agreement_rate`, `avg_latency_sec`.

## 4. Tác động định lượng sau thay đổi
- Regression score: V1 = 2.2323, V2 = 4.8182, delta = +2.59.
- Pass rate benchmark hiện tại: 94/99 = 94.95%.
- Retrieval hit rate và agreement rate đạt mức cao, release gate ở trạng thái APPROVE.