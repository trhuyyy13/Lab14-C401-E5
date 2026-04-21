# Báo Cáo Cá Nhân  

**Họ và tên:** Lê Hoàng Đạt  
**Mã:** 2A202600377  

Trong bài lab này, tôi đã hoàn thành đầy đủ các nhiệm vụ chính được nêu trong README và đưa hệ thống đánh giá AI từ trạng thái mẫu sang trạng thái có thể chạy benchmark thực tế. Mục tiêu của tôi không chỉ là làm cho chương trình chạy được, mà còn là đảm bảo toàn bộ pipeline có số liệu rõ ràng để đo chất lượng Retrieval, Generation, chi phí và độ ổn định của agent.

## 1. Retrieval & SDG

Tôi đã xây dựng script sinh Golden Dataset với tối thiểu 50 test cases, có gắn `ground truth retrieval ids` để phục vụ đánh giá Hit Rate và MRR. Trong quá trình làm, tôi không để dữ liệu sinh ra chỉ là câu hỏi ngẫu nhiên mà thiết kế theo nhiều nhóm tình huống như hard case, ambiguous, conflicting information, out-of-context, latency stress và cost efficiency.

Ngoài ra, tôi đã xử lý lại dữ liệu đầu vào trước khi chunk để giảm nhiễu từ file txt gốc. Tôi tạo một bước clean dữ liệu dùng chung cho cả phần sinh bộ test và phần agent retrieval, giúp chunking nhất quán hơn và tránh lệch id giữa bộ gold và index retrieval. Đây là điểm quan trọng vì nếu chunk không đồng bộ thì `expected_retrieval_ids` sẽ không còn khớp với chunk thực tế.

## 2. Eval Engine & Multi-Judge Consensus

Tôi đã hoàn thiện phần đánh giá để hệ thống không chỉ chấm câu trả lời theo một tiêu chí đơn lẻ mà còn đo được nhiều chỉ số cùng lúc, bao gồm Retrieval Accuracy, Hit Rate, Average Hit Rate, MRR, Final Answer Accuracy, Hallucination Rate, Average Score, Latency, Cost và User Satisfaction Score.

Tôi cũng triển khai cơ chế multi-judge với ít nhất 2 model judge khác nhau, gồm `gpt-4o` và `gpt-4o-mini`. Hệ thống có tính `Agreement Rate` và xử lý xung đột điểm số theo logic tổng hợp, thay vì phụ thuộc vào một model duy nhất. Điều này giúp kết quả đánh giá ổn định và sát thực tế hơn.

## 3. Benchmark, Regression Gate và Phân tích kết quả

Tôi đã nối toàn bộ pipeline vào `main.py` để chạy benchmark tự động, tạo các file báo cáo `reports/summary.json` và `reports/benchmark_results.json`. Từ đó, hệ thống có thể so sánh giữa hai cấu hình/phiên bản agent và đưa ra quyết định release hoặc block release dựa trên kết quả thực tế.

Trong quá trình benchmark, tôi cũng theo dõi các lỗi chính của retrieval và điều chỉnh lại chunking, reranking và cách sinh câu hỏi để giảm tụt metric. Việc này giúp tôi xác định nguyên nhân gốc rễ của vấn đề nằm ở sự không đồng bộ giữa dữ liệu sinh và cách agent cắt chunk, chứ không chỉ do mô hình trả lời yếu.

## 4. Tối ưu Agent

Tôi đã thay phần agent mẫu bằng một agent thật dùng retrieval nội bộ, sau đó cải tiến theo hướng hybrid retrieval, bổ sung reranker và hỗ trợ embedding-based retrieval khi có API key. Tôi cũng tối ưu lại câu hỏi sinh ra để bám chunk hơn, giúp Top-1 retrieval tốt hơn và hạn chế việc hệ thống trả lời lan man hoặc bịa thông tin ngoài ngữ cảnh.

## 5. Kết quả đạt được

Sau khi hoàn tất, tôi đã có một hệ thống evaluation có thể chạy end-to-end: sinh dữ liệu, chunk dữ liệu, truy hồi, chấm điểm, tổng hợp báo cáo và so sánh regression. Kết quả benchmark cuối cùng cho thấy pipeline đã ổn định hơn, Retrieval và MRR được cải thiện rõ rệt, đồng thời báo cáo đầu ra đã đầy đủ để nộp bài theo yêu cầu.

## 6. Kết luận cá nhân

Các bài học tôi rút ra rõ nhất sau quá trình triển khai:

- Đồng bộ dữ liệu quan trọng hơn tối ưu prompt đơn lẻ: nếu bước clean/chunk giữa SDG và retrieval không thống nhất thì metric sẽ giảm mạnh ngay cả khi câu trả lời trông hợp lý.
- Đánh giá đa tiêu chí giúp nhìn đúng chất lượng hệ thống: cần theo dõi đồng thời Retrieval, Accuracy, Hallucination, Latency và Cost để tránh tối ưu lệch một chỉ số.
- Multi-judge giúp tăng độ tin cậy của kết quả chấm: dùng từ 2 judge trở lên và theo dõi agreement rate giúp giảm rủi ro thiên lệch của một model.
- Benchmark phải có khả năng lặp lại: pipeline tự động từ sinh data đến xuất report là điều kiện cần để so sánh phiên bản agent khách quan.
- Cần ưu tiên xử lý nguyên nhân gốc trước tối ưu bề mặt: khi metric giảm, phải kiểm tra ingestion/chunking/retrieval trước khi chỉnh phần generation.

## 7. Minh chứng

Các minh chứng cho phần việc tôi đã hoàn thành:
- Hoàn thành sinh bộ test chuẩn benchmark: dữ liệu đã được tạo lại với 50 cases trong file data/golden_set.jsonl.
- Hoàn thành báo cáo benchmark đầu ra: hệ thống sinh đầy đủ reports/summary.json và reports/benchmark_results.json sau khi chạy main.py.
- Hoàn thành kiểm tra định dạng nộp bài: chạy check_lab.py thành công, không lỗi thủ tục.
- Hoàn thành các metric chính theo yêu cầu README: Retrieval Accuracy, Hit Rate, MRR, Final Answer Accuracy, Hallucination Rate, Average Score, Latency, Cost, User Satisfaction Score.
- Kết quả benchmark gần nhất (theo reports/summary.json): retrieval_accuracy = 0.76, hit_rate = 0.80, mrr = 0.78, final_answer_accuracy = 0.71224, hallucination_rate = 0.16, avg_score = 4.3954, user_satisfaction_score = 4.5648.
