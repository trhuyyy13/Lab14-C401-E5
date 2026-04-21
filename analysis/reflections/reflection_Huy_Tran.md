# Reflection - Huy Trần

## 1) Vai trò & Phạm vi đóng góp

- **Vai trò trong team:** Fullstack Engineer (Data, Retrieval, AI Judge, Analyst, DevOps)
- **Module phụ trách:** Toàn bộ dự án, bao gồm xử lý dữ liệu (`data/legal_chunker.py`, `data/synthetic_gen.py`), xây dựng Agent (`agent/main_agent.py`, `engine/retrieval_eval.py`, `engine/llm_judge.py`, `engine/async_runner.py`), và Regression Pipeline (`main.py`).
- **File/chức năng đã chỉnh sửa:** Thiết kế Hybrid chunking, định nghĩa cơ chế Multi-Judge Consensus kết hợp phân tích nguyên nhân gốc rễ.

## 2) Đóng góp kỹ thuật chính

- **Data & Retrieval:** Triển khai lại từ đầu chunking strategy theo Điều/Khoản để tránh đứt gãy context khi xử lý văn bản pháp lý. Khởi tạo tự động 60 test cases có nhãn id chuẩn phục vụ cho việc tính toán Hit Rate.
- **Consensus & Evaluation:** Phát triển Multi-Judge Pipeline hoạt động không đồng bộ (Asynchronous) để tối ưu về thời gian. Sử dụng thuật toán hiệu chỉnh Agreement Rate nhằm thống nhất kết quả đánh giá tự động.
- **Auto-Gate/Regression:** Viết mã lệnh đánh giá tính cạnh tranh giữa 2 models (Agent_V1_Base và Agent_V2_Optimized), qua đó xác thực V2 vượt trội một cách tự động và chấp nhận bản cập nhật (APPPROVE).

## 3) Kết quả đo được

- Retrieval Metrics cực kỳ tích cực (Hit Rate = **85.0%**).
- Điểm đánh giá Judge trung bình cải thiện lớn so với V1 (Từ 2.45 lên **4.27/5**).
- Mức độ đồng thuận (Agreement Rate) ở mức **92.5%**.
- Độ trễ tối ưu chỉ **2.03s/case**; chi phí ~0.019 USD cho 60 truy vấn.

## 4) Vấn đề gặp phải & cách xử lý

- **Vấn đề kỹ thuật:** Quá tải memory hoặc Timeout trong quá trình xử lý 60 cases chạy đánh giá bằng các model cùng lúc. LLM đôi lúc bất đồng quan điểm khi câu trả lời liên quan tới pháp chế đặc thù, yes/no phi logic.
- **Cách debug:** Thu hẹp batch request; in log lỗi fetch context bị trượt.
- **Giải pháp:** Sử dụng Async Runner để limit số task chạy đồng thời, đồng thời áp prompt template mạch lạc cho bộ 2 Judge để tiêu chuẩn hoá Output criterion.

## 5) Bài học rút ra

- Sự thành bại của hệ thống AI phụ thuộc hơn 70% vào chất lượng ở bước truy hồi (Retrieval). Retriever dở thì Generator tốt mấy cũng dẫn đến hallucination.
- Làm độc lập tốn khá nhiều sức vào pipeline devops và debug nhưng có lợi thế ở việc hiểu từ ngọn ngành gốc rễ từng metrics.

## 6) Kế hoạch cải tiến cá nhân

- **Kế hoạch cải tiến:** Viết thêm bộ Rewriter để bóc tách các câu hỏi dạng phức/nhiều lớp, từ đó kéo rank của các chunk chính xác lên top 1 trong tương lai. Nâng cấp các file log chi phí theo ngày.
