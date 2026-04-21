# Reflection - Lương Tiến Dũng

## Module phụ trách
- [x] Hệ thống chỉ số đánh giá (Evaluation Metrics)
- [x] Dashboard Visualization & UX
- [x] Cross-platform Stability (Windows Compatibility)
- [x] Báo cáo phân tích Failure Analysis

## Đóng góp kỹ thuật chính

### 1. Nâng cấp hệ thống chỉ số RAGAS & Agent Metrics
Tôi đã trực tiếp thiết kế và tích hợp bộ chỉ số đa chiều để đánh giá toàn diện chất lượng Agent:
- Triển khai **Hallucination Rate** (1 - Faithfulness) để đo lường độ tin cậy của câu trả lời.
- Xây dựng công thức **User Satisfaction Score** (kết hợp giữa Accuracy và Latency) giúp đánh giá trải nghiệm thực tế của người dùng.
- Chuẩn hóa **Final Answer Accuracy** từ AI Judge để cung cấp cái nhìn trực quan về độ chính xác nội dung so với Ground Truth.

### 2. Tối ưu hóa Dashboard & Real-time Monitoring
Để cải thiện trải nghiệm người dùng khi vận hành hệ thống đánh giá:
- Tái cấu trúc bố cục Dashboard sang dạng **Grid-layout**, giúp quan sát toàn bộ biểu đồ KPIs (Score, Status, Latency, Category) trên một màn hình duy nhất mà không cần cuộn trang.
- Chuyển đổi các biểu đồ thô sang dạng **Donut Chart (Altair)** chuyên nghiệp, tăng tính tương tác và thẩm mỹ.
- Thực hiện **Real-time Log Streaming** thông qua xử lý bất đồng bộ, loại bỏ tình trạng treo giao diện khi chạy Benchmark và hiển thị tiến trình minh bạch cho người dùng.

### 3. Đảm bảo tính ổn định và tương thích hệ thống
- Xử lý triệt để các lỗi `UnicodeEncodeError` trên môi trường Windows bằng cách chuẩn hóa bảng mã cho toàn bộ log hệ thống trong `main.py`, `dashboard.py` và `check_lab.py`.
- Thiết lập hệ thống **Regression Banners** hiển thị rõ ràng thông tin phiên bản Agent và mô hình AI Judge đang sử dụng, tăng tính minh bạch cho quy trình kiểm thử.

## Bài học rút ra
- Việc xây dựng một hệ thống đánh giá tự động (Auto-eval) quan quan trọng tương đương với việc xây dựng chính Agent đó, vì nó cung cấp "la bàn" để tối ưu hóa mô hình.
- Trải nghiệm người dùng (UX) trong các công cụ kỹ thuật như Dashboard giúp việc chẩn đoán lỗi nhanh hơn và giảm thiểu sai sót trong quá trình vận hành.

## Minh chứng
- **File thực hiện**: `main.py`, `dashboard.py`, `check_lab.py`, `analysis/failure_analysis.md`.
- **Kết quả Benchmark**: Tổng số 80 cases, Pass Rate 97.5%, Avg Score 4.10, User Satisfaction 85.6%.
- **Trạng thái**: Hệ thống đã vượt qua mọi bước kiểm tra của `check_lab.py` và sẵn sàng nộp bài.
