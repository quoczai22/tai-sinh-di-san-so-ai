# Lệnh “số dư” của bot Zalo

Lệnh này chỉ dành cho ID chat riêng của người vận hành (`ALERT_ZALO_USER_CHAT_ID`). Bot đọc **mức chi toàn tài khoản AWS đã ghi nhận trong Budget tháng**, không gọi GPU và không có quyền triển khai. Budget 5 USD là ngưỡng gửi cảnh báo, không phải số dư hay khóa cứng chi tiêu. [AWS Budgets có thể cập nhật trễ nhiều giờ](https://docs.aws.amazon.com/cost-management/latest/userguide/bcm-lite-view-budget.html).

Modal Starter chưa có API báo cáo billing chính thức cho bot. Credit và Spend limit Modal phải xem tại **Modal → Settings → Usage & Billing**. Bot không ước tính credit từ số lượt sinh hoặc giá GPU.

## Dòng dữ liệu

1. Vercel nhận `/checkcredit` từ chat riêng đã xác thực bằng webhook secret và allowlist.
2. Vercel lấy token OIDC ngắn hạn của đúng project Production, đổi sang AWS role `tai-sinh-di-san-so-ai-budget-read`. Bot không giữ AWS access key, không tạo endpoint công khai và không giữ Modal token.
3. Role chỉ được gọi `budgets:ViewBudget` cho Budget `tai-sinh-di-san-so-ai-aws-5usd`.
4. Bot chỉ hiển thị `ActualSpend` và `BudgetLimit` nếu API trả dữ liệu USD hợp lệ. Lỗi hoặc thiếu cấu hình thì báo “chưa xác minh”, không dùng số mặc định.

IAM provider và role khai báo ở `scripts/deploy/aws-budget-oidc.yaml`. Project Vercel phải bật **Secure backend access with OIDC federation**, chọn **Team issuer**; team slug là `quoczai22s-projects`. Sau khi deploy stack, đặt output `BudgetReadRoleArn` vào biến `AWS_BUDGET_ROLE_ARN` của Vercel Production. Không cấp role cho Preview hay project khác. Kiểm tra lệnh bot trong chat riêng và xác nhận số khớp với AWS Budget Console. Nếu role bị từ chối, bot báo chưa xác minh.
