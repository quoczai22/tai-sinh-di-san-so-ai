### Đề Xuất Cải Tiến Nâng Cấp Hệ Thống "Tái Sinh Di Sản Số": Tự Động Hóa Sinh Hoa Văn Gốm Bát Tràng Lên Áo Dài

#### 1\. Đặt Vấn Đề & Phân Tích Hiện Trạng Hệ Thống MVP

Dự án "Tái Sinh Di Sản Số" được phát triển nhằm mục tiêu chuyển đổi số di sản văn hóa gốm Bát Tràng và ứng dụng tự động lên áo dài Việt Nam bằng trí tuệ nhân tạo sinh ảnh. Phiên bản thử nghiệm khả thi tối thiểu (MVP) đã đạt được bước đột phá quan trọng khi gỡ bỏ triệt để "xung đột hình học" giữa kiểu dáng hiện vật gốm cổ và phom dáng áo dài truyền thống.  
Bằng việc chuyển đổi từ kiến trúc đơn giai đoạn (1-stage) sang kiến trúc hai giai đoạn (2-stage), hệ thống MVP đã tách biệt hoàn toàn việc sinh hoa văn phẳng với quy trình dán họa tiết lên trang phục. Ở Giai đoạn 1, hệ thống loại bỏ đường bao hiện vật gốm bằng kỹ thuật co mask 14 pixel và áp dụng điều kiện Canny Edge qua ControlNet v1.1 cùng tính năng  *Circular Padding*  trên mạng U-Net và VAE của Stable Diffusion v1.5 để tạo ra hoa văn phẳng lặp liền mép. Ở Giai đoạn 2, hệ thống cố định phom dáng áo dài bằng ảnh mẫu phông trắng chuẩn (sinh từ seed 43 với prompt bổ sung chi tiết cấu trúc cổ trụ, tay dài, hai tà xẻ từ eo) và tiến hành ghép họa tiết tất định qua các phép toán hình học (Displacement Map, Shading Map, khớp màu không gian LAB), sau đó hoàn thiện bằng luồng img2img nhẹ ở mức khử nhiễu ( *denoise strength* ) 0.40.  
Mặc dù hệ thống MVP đã chứng minh được tính khả thi kỹ thuật trên hạ tầng GPU cục bộ 8 GB VRAM (chỉ chiếm đỉnh 3.33 GB VRAM và mất 2 phút 41 giây để tạo một bộ 4 thiết kế), kết quả phân tích nghiệm thu kỹ thuật vẫn chỉ ra năm hạn chế cốt lõi cần giải quyết:

* **Bóng dáng hiện vật gốc chưa được triệt tiêu hoàn toàn:**  Trong Giai đoạn 1, ở các mức trọng số ControlNet cao, các vệt cạnh ranh giới của bình gốm vẫn còn in bóng chìm lên hoa văn phẳng.  
* **Kỹ thuật lặp Seamless còn đơn giản:**  Việc áp dụng  *Circular Padding*  ở cấp độ lớp tích chập (Conv2d) chỉ giúp khép kín biên cơ bản, dễ gây hiện tượng lặp lại mảng khối thiếu tự nhiên khi mở rộng hoa văn lên độ phân giải lớn.  
* **Quy trình hòa trộn Giai đoạn 2 mang tính cào bằng:**  Luồng img2img áp dụng mức khử nhiễu cố định 0.40 trên toàn bộ bề mặt áo dài, khiến cho một số chi tiết nét hoa văn di sản tinh xảo bị mờ nhòe trong khi các nếp gấp vải chưa đạt độ đổ bóng tự nhiên sâu.  
* **Sự phụ thuộc vào mẫu áo phông trắng cố định:**  Kỹ thuật bóc tách vùng áo dựa vào độ bão hòa thấp và độ sáng cao hiện chỉ áp dụng được trên vải trắng, ngăn cản khả năng mở rộng sang các mẫu trang phục đa dạng màu sắc hoặc nhiều tư thế thực tế.  
* **Thiếu các bộ chỉ số đánh giá cấu trúc và ngữ nghĩa sâu:**  Hệ thống hiện mới dừng lại ở điểm tương đồng CLIP (Visual Similarity) và đo độ đệm seam, chưa đo lường được độ giữ nguyên cấu trúc đường nét hình học và tri thức di sản ngữ nghĩa.

Bản đề xuất này hoạch định giải pháp nâng cấp toàn diện hệ thống thông qua bốn trụ cột kỹ thuật cốt lõi, tích hợp các thành tựu nghiên cứu tiên tiến nhất từ các công trình công bố quốc tế trong tập nguồn tri thức của dự án.  
Hạng Mục Kỹ Thuật,Hiện Trạng MVP (SD1.5 2-Stage),Giải Pháp Cải Tiến Đề Xuất,Nguồn Nghiên Cứu Tham Chiếu  
Sinh hoa văn phẳng Seamless,"Circular Padding trên Conv2d (UNet+VAE), seam diff 12.6",Noise Rolling \+ Latent Replication \+ LoRA / IP-Adapter,"Structured Pattern Expansion ,  Tiled Diffusion"  
Bảo tồn nét & Phong cách,"ControlNet Canny trên SD1.5 đóng băng, co mask 14px",Fine-tuning LoRA ranh giới nhẹ \+ ControlNet theo vùng ( Masked ControlNet ),"Blue Calico ,  Kizil Rhombic Mural ,  Dunhuang DANet"  
Hòa trộn hoa văn lên áo dài,img2img cố định denoise 0.40 toàn bộ áo dài,Differential Diffusion (Continuous Strength Map  \$\\mu\$ ) \+ Semantic Segmentation,"Differential Diffusion ,  TexControl ,  TPD Virtual Try-On"  
Đánh giá & Kiểm định,"Visual Similarity (CLIP), Seam Diff, khảo sát sơ bộ","SAS (Hough Line), SSIM/LPIPS, WiScore (WISE Framework)","WISE Benchmark ,  Verifiable Human Eval ,  Paper Ulos"

#### 2\. Trụ Cột 1: Tự Động Sinh Hoa Văn Seamless & Tinh Chỉnh Miền Họa Tiết

Hạn chế lớn nhất ở Giai đoạn 1 của hệ thống hiện tại là sự đánh đổi giữa độ bám đường nét cổ và hiện tượng "lộ bóng dáng bình" khi tăng trọng số ControlNet. Nhằm giải quyết triệt để vấn đề này, kiến trúc Giai đoạn 1 được tái thiết kế dựa trên sự kết hợp giữa kỹ thuật mở rộng họa tiết cấu trúc và tinh chỉnh mô hình thích ứng thứ hạng thấp (LoRA).

##### 2.1. Kiến Trúc Mở Rộng Họa Tiết Bằng Noise Rolling Và Latent Replication

Thay vì chỉ áp dụng đệm tròn ( *Circular Padding* ) vốn dễ lộ vết ranh giới lặp lại khi phóng to họa tiết, hệ thống đề xuất tích hợp thuật toán  **Noise Rolling**  và  **Latent Replication**  được chứng minh hiệu quả trong nghiên cứu về mở rộng họa tiết cấu trúc ( *Structured Pattern Expansion* ).  
Trong mỗi bước khử nhiễu  \$t\$  của quá trình khuếch tán không gian ẩn, ma trận ẩn  \$z\_t\$  được dịch chuyển vòng xoay ( *cyclic shift* ) theo chiều ngang  \$\\Delta x\$  và chiều dọc  \$\\Delta y\$  trước khi đưa qua U-Net, sau đó được dịch chuyển ngược lại để trả về cấu hình ban đầu:  
\$\$z'\_t \= \\text{roll}(z\_t, \\Delta x, \\Delta y)\$\$  
\$\$z\_{t-1} \= \\text{roll}(z'\_{t-1}, \-\\Delta x, \-\\Delta y)\$\$  
Thao tác dịch chuyển ma trận ẩn này giúp mở rộng trường tiếp nhận ( *receptive field* ) của U-Net, buộc mô hình coi các đường biên của hoa văn là liên tục và tự động triệt tiêu các đường nối thị giác ( *seams* ). Để mở rộng hoa văn lên độ phân giải cao tùy ý mà không làm thay đổi nét vẽ gốc, hệ thống thực hiện  **Latent Replication**  tại thời điểm 60% tiến trình khử nhiễu (bước  \$N \= 0.6 \\times T\$ ), nhân bản ma trận ẩn ra quy mô canvas mục tiêu và tiếp tục chạy các bước khử nhiễu còn lại dưới cơ chế khử nhiễu theo mảng ( *patched diffusion* ).

##### 2.2. Huấn Luyện LoRA Tối Ưu Bản Sắc Men Gốm Kết Hợp IP-Adapter

Để loại bỏ sự phụ thuộc hoàn toàn vào ControlNet Canny (nguyên nhân chính gây lộ bóng dáng vật chứa ở weight cao), hệ thống sẽ huấn luyện một mô hình  **LoRA nhẹ**  (Low-Rank Adaptation) chuyên biệt cho miền hoa văn gốm Bát Tràng, dựa trên phương pháp đã thành công ở dự án bảo tồn vải Blue Calico và họa tiết bích họa Kizil.

1. **Xây dựng Dataset chuẩn hóa:**  Thu thập và đóng gói 300–500 ảnh hoa văn gốm Bát Tràng phẳng (đã bóc tách khỏi hiện vật), phân loại theo các nhóm họa tiết chính (rồng, hoa cúc dây, mây cuộn, sóng nước, hình thoi).  
2. **Gán nhãn đa thức (Multimodal Captioning):**  Mô tả từng ảnh bằng cặp từ khóa ngữ nghĩa chi tiết kết hợp thuật toán CLIP Encoder để mô hình học chính xác đặc trưng màu men xanh lam, men rạn, và nét vẽ nét bút lông cổ.  
3. **Tiêm LoRA vào mạng U-Net:**  Tinh chỉnh các ma trận trọng số bổ trợ  \$\\Delta \\Theta \= A \\cdot B\$  vào các lớp Self-Attention và Cross-Attention của U-Net với rank  \$r=8\$  hoặc  \$r=16\$ , giữ nguyên đóng băng các trọng số gốc của Stable Diffusion.  
4. **Tích hợp IP-Adapter làm tín hiệu hướng dẫn (Guidance Image):**  Trích xuất vector đặc trưng hình ảnh từ hiện vật gốm gốc thông qua IP-Adapter, đưa trực tiếp vào U-Net song song với điều kiện prompt chữ.

Sự kết hợp giữa LoRA và IP-Adapter giúp mô hình tự có tri thức nội tại về phong cách gốm Bát Tràng, cho phép giảm trọng số ControlNet Canny từ  \$w=0.85\$  xuống  \$w=0.35–0.45\$  mà vẫn giữ nguyên độ chính xác của hoa văn cổ, hoàn toàn xóa bỏ bóng dáng chiếc bình gốm gốc.

#### 3\. Trụ Cột 2: Hòa Trộn Vi Mô Bằng Differential Diffusion & Tách Vùng Phân Đoạn

Giai đoạn 2 của hệ thống đóng vai trò quyết định tính thẩm mỹ và độ chân thực khi đưa hoa văn lên áo dài. Quy trình hiện tại sử dụng phép ghép tất định (Displacement/Shading) kết hợp img2img toàn cục ở denoise 0.40. Tuy nhiên, mức denoise phẳng này làm suy giảm chi tiết hoa văn ở vùng trung tâm áo và chưa tạo đủ độ sâu cho nếp gấp vải.

##### 3.1. Cơ Chế Điều Khai Khử Nhiễu Vi Mô Qua Continuous Change Map

Hệ thống đề xuất thay thế luồng img2img tiêu chuẩn bằng phương pháp  **Differential Diffusion**  (Khuếch tán vi phân). Kỹ thuật này cho phép người dùng hoặc hệ thống định nghĩa một bản đồ độ thay đổi ( *Continuous Change Map* )  \$\\mu\$  có giá trị liên tục từ  \$0.0\$  đến  \$1.0\$  cho từng vị trí không gian trên ảnh áo dài.  
Thay vì áp dụng cùng một lực khử nhiễu cho toàn bộ bức ảnh, Differential Diffusion phân rã bản đồ  \$\\mu\$  thành các mặt nạ lồng nhau ( *nested masks* ) theo từng bước thời gian  \$t\$ . Mặt nạ tại bước  \$t\$  được xác định qua công thức:  
\$\$\\text{mask}\_t \= \\mu \\le \\frac{k \- t}{k}\$\$  
Trong đó  \$k\$  là tổng số bước suy luận. Ma trận ẩn trung gian  \$z\_t\$  tại mỗi bước được hòa trộn giữa ma trận ẩn vừa khử nhiễu  \$z\_{t+1}\$  và ma trận ẩn được bơm nhiễu lại từ ảnh gốc  \$z'\_t\$ :  
\$\$z\_t^{\\text{mix}} \= z\_t \\odot \\text{mask}\_t \+ z'\_t \\odot (1 \- \\text{mask}\_t)\$\$  
Bằng cách này, hệ thống thiết lập bản đồ thay đổi  \$\\mu\$  đa tầng cho chiếc áo dài:

* **Vùng hoa văn ngực và tà áo chính:**  Đặt  \$\\mu \= 0.15 \- 0.25\$  (mức denoise rất nhẹ), bảo tồn 100% độ sắc nét và màu sắc gốc của hoa văn gốm từ Giai đoạn 1\.  
* **Vùng biên áo dài và nếp gấp vắt qua eo:**  Đặt  \$\\mu \= 0.50 \- 0.65\$  (mức denoise cao hơn), cho phép AI tự do tái tạo ánh sáng, nếp rủ và cấu trúc sợi lụa tự nhiên.  
* **Vùng phông nền và quần lụa:**  Đặt  \$\\mu \= 0.0\$  (cố định tuyệt đối), giữ nguyên độ sạch và phom dáng phông nền.

       BẢN ĐỒ KHỦ NHIỄU VI PHÂN (DIFFERENTIAL STRENGTH MAP)  
\+---------------------------------------------------------------+  
\|                      Phông nền: µ \= 0.00                      \|  
\|                  (Cố định hoàn toàn phông)                    \|  
\|                                                               \|  
\|                   Cổ trụ / Vai: µ \= 0.15                      \|  
\|                 (Bảo tồn nét hoa văn tuyệt đối)               \|  
\|                                                               \|  
\|                 Thân áo / Ngực: µ \= 0.20                      \|  
\|                 (Giữ hoa văn gốm mịn màng)                    \|  
\|                                                               \|  
\|                 Nếp gấp eo / Tà rủ: µ \= 0.55                  \|  
\|               (Tạo bóng đổ & nếp vải mềm mại)                 \|  
\|                                                               \|  
\|                      Quần lụa: µ \= 0.00                       \|  
\+---------------------------------------------------------------+

##### 3.2. Tự Động Phân Đoạn Vùng Áo Bằng Semantic Segmentation

Để thoát khỏi hạn chế của thuật toán tách nền dựa vào độ bão hòa màu trắng, hệ thống nâng cấp bộ phân đoạn vùng áo bằng mô hình suy luận ngữ nghĩa  **Semantic Segmentation**  (tương tự kiến trúc Decoupled Mask Prediction trong nghiên cứu Texture-Preserving Diffusion). Mô hình tự động trích xuất các mặt nạ vùng chi tiết ( *garment masks* ): thân trước, thân sau, tay áo, cổ áo và nếp vải. Điều này cho phép ứng dụng hệ thống trên bất kỳ ảnh mẫu áo dài nào (nhiều màu sắc, chất liệu vải khác nhau, hoặc người mẫu thật) mà không bị phụ thuộc vào phông nền trắng.

#### 4\. Trụ Cột 3: Tối Ưu Tốc Độ Suy Luận & Hiệu Năng Hạ Tầng GPU

Hệ thống hiện tại cần trung bình 2 phút 41 giây để tạo một bộ 4 thiết kế trên GPU 8 GB VRAM. Nhằm mục tiêu chuyển giao công cụ phục vụ các trải nghiệm tương tác trực tiếp tại bảo tàng, điểm du lịch hoặc ứng dụng Web UI thời gian thực, hệ thống đề xuất ba giải pháp tối ưu hóa hiệu năng hạ tầng:

##### 4.1. Tích Hợp Mô Hình Nhất Quán Ẩn (Latent Consistency Model \- LCM)

Dựa trên kinh nghiệm từ mô hình sinh thời trang hai giai đoạn  *TexControl* , hệ thống sẽ tích hợp ma trận chèn  **LCM LoRA**  vào Stable Diffusion. Kỹ thuật này nén đường cong khử nhiễu của LDM, cho phép tạo ảnh chất lượng cao chỉ với  **4 đến 8 bước lấy mẫu**  (thay vì 30 bước như hiện tại). Tốc độ sinh hoa văn phẳng ở Giai đoạn 1 nhờ đó được rút ngắn từ 6.5 giây xuống còn  **0.8–1.2 giây/ảnh** .

##### 4.2. Tối Ưu Số Bước Lấy Mẫu Theo Phép Đo SSIM

Kết quả thực nghiệm trên bài báo sinh hoa văn dệt Ulos chứng minh rằng việc tăng quá mức số bước suy luận không đồng nghĩa với việc tăng chất lượng hoa văn. Phân tích chỉ số độ tương đồng cấu trúc ( **SSIM** ) cho thấy quá trình lấy mẫu đạt đỉnh cân bằng tại  **30 bước DDIM**  ( \$\\text{SSIM} \= 0.7103\$ ). Việc nâng lên 40 hay 50 bước làm hiện tượng khử nhiễu quá đà xuất hiện, gây biến dạng các góc nét hoa văn cổ. Do đó, hệ thống chuẩn hóa số bước suy luận ở mức 25–30 bước cho chế độ sinh độ phân giải cao và 6 bước cho chế độ xem trước nhanh ( *Fast Preview* ).

##### 4.3. Quản Lý Bộ Nhớ VRAM Động Và Biên Dịch Mô Hình

Với đỉnh VRAM hiện tại là 3.33 GB trên tổng số 8 GB của card đồ họa, hệ thống còn dư 58% tài nguyên bộ nhớ. Hệ thống sẽ áp dụng các kỹ thuật nén và tăng tốc sau:

* **Nạp sẵn mô hình lên VRAM (Model Caching):**  Giữ cố định U-Net, VAE, và ControlNet trên VRAM giữa các yêu cầu người dùng, xóa bỏ thời gian nạp/xả mô hình từ RAM hệ thống (tiết kiệm 12–15 giây mỗi lượt sinh).  
* **Biên dịch TensorRT / torch.compile:**  Biên dịch tĩnh đồ thị tính toán U-Net, tăng tốc độ tính toán ma trận lên 35%.  
* **Nâng cấp độ phân giải nội tại:**  Tăng kích thước sinh hoa văn phẳng từ  \$512 \\times 512\$  pixel lên  \$1024 \\times 1024\$  pixel (tương thích SDXL hoặc SD1.5 Upscaled) để cung cấp tệp in chất lượng cao cho các cơ sở sản xuất vải.

#### 5\. Trụ Cột 4: Chuẩn Hóa Bộ Chỉ Số Đánh Giá Định Lượng & WiScore

Một hệ thống AI ứng dụng trong di sản văn hóa đòi hỏi quy trình đánh giá tính chính xác nghiêm ngặt, minh bạch và có thể tái lập. Đề xuất mở rộng bộ chỉ số đánh giá từ cấp độ độ nét hình học đến cấp độ hiểu biết ngữ nghĩa sâu.

##### 5.1. Bộ Chỉ Số Đánh Giá Cấu Trúc Hình Học (SAS, SSIM, Seam Line)

Hệ thống bổ sung chỉ số  **SAS (Structural Adherence Score)**  được phát triển trong nghiên cứu bích họa Kizil. Thuật toán sử dụng phép biến đổi đường  **Hough Line Transform**  trên ảnh hoa văn đầu ra để đo đạc chính xác tỉ lệ % ảnh bảo tồn đúng các đường nét hình học song song và góc nghiêng chuẩn của di sản gốc.  
Song song đó, độ đệm lặp mép được kiểm soát nghiêm ngặt qua phép đo  **Seam Discontinuity Value**  (yêu cầu chỉ số chênh lệch ranh giới  \$\< 13.6\$ ).  
\$\$SAS \= \\frac{N\_{\\text{valid\\\_hough\\\_lines}}}{N\_{\\text{total\\\_expected\\\_lines}}} \\times 100\\%\$\$

##### 5.2. Đánh Giá Ngữ Nghĩa Di Sản Theo Framework WISE (WiScore)

Nhằm khắc phục điểm yếu của chỉ số CLIP-Score vốn bị hạn chế bởi cơ chế "túi chứa từ" ( *bag-of-words* ) và không đo được tri thức di sản ngữ nghĩa, hệ thống đề xuất áp dụng chuẩn đánh giá  **WISE (World Knowledge-Informed Semantic Evaluation)**  với chỉ số tổng hợp  **WiScore** :  
\$\$\\text{WiScore} \= 0.7 \\times \\text{Consistency} \+ 0.2 \\times \\text{Realism} \+ 0.1 \\times \\text{Aesthetic Quality}\$\$  
Hệ thống tích hợp một mô hình Multimodal LLM (như GPT-4o hoặc VLM chuyên dụng) làm bộ chấm điểm tự động, đưa ra đánh giá dựa trên 3 tiêu chí:

* **Consistency (Độ nhất quán tri thức di sản \- Trọng số 70%):**  Kiểm tra xem hoa văn sinh ra có thể hiện đúng các biểu tượng đặc trưng của gốm Bát Tràng (ví dụ: hoa cúc dây thời Lê-Trịnh, rồng mây thời Nguyễn, màu men lam đặc trưng) hay không.  
* **Realism (Tính chân thực chất liệu \- Trọng số 20%):**  Đánh giá hiệu ứng hòa trộn hoa văn vào bề mặt vải lụa áo dài.  
* **Aesthetic Quality (Tính thẩm mỹ mỹ thuật \- Trọng số 10%):**  Đánh giá bố cục và sự hài hòa màu sắc tổng thể của trang phục.

##### 5.3. Chuẩn Hóa Quy Trình Khảo Sát Người Dùng (Human Evaluation Protocol)

Dựa trên hướng dẫn chuẩn hóa đánh giá người dùng ( *Verifiable Human Evaluation* ), hệ thống xây dựng giao diện khảo sát trực quan cho 30–50 người tham gia (gồm chuyên gia di sản, nhà thiết kế thời trang và người dùng trẻ). Khảo sát đánh giá độc lập 4 biến thể thiết kế theo thang điểm Likert 5 mức trên 3 trục: Tính nhận diện di sản gốc, Tính thẩm mỹ ứng dụng thời trang, và Độ tự nhiên của phom dáng áo dài.

#### 6\. Lộ Trình Triển Khai & Quản Lý Rủi Ro Kỹ Thuật

Kế hoạch cải tiến hệ thống được chia làm bốn giai đoạn triển khai cuốn chiếu trong thời gian 12 tuần, đảm bảo tính liên tục của phần mềm và khả năng kiểm soát rủi ro kỹ thuật.

##### 6.1. Các Giai Đoạn Triển Khai Kỹ Thuật

* **Giai đoạn 1 (Tuần 1 – Tuần 3): Đóng gói dữ liệu & Huấn luyện LoRA Gốm Bát Tràng**  
* Thu thập 500 mẫu hoa văn phẳng gốm Bát Tràng chuẩn hóa.  
* Huấn luyện mô hình LoRA trên SD1.5 kết hợp IP-Adapter.  
* Thử nghiệm đánh giá định lượng FID, IS và SAS trên tập hoa văn sinh ra.  
* **Giai đoạn 2 (Tuần 4 – Tuần 6): Tích hợp Noise Rolling & Differential Diffusion**  
* Cài đặt thuật toán Noise Rolling và Latent Replication vào luồng sinh Giai đoạn 1\.  
* Tích hợp module Differential Diffusion với Continuous Change Map vào Giai đoạn 2\.  
* Thử nghiệm khả năng bóc tách dáng bằng mô hình Semantic Segmentation.  
* **Giai đoạn 3 (Tuần 7 – Tuần 9): Tối ưu hóa tốc độ & Nâng cấp Web UI**  
* Tích hợp LCM LoRA để rút ngắn bước suy luận xuống 6–8 bước.  
* Đóng nạp mô hình cố định trên VRAM và biên dịch đồ thị TensorRT.  
* Xây dựng giao diện so sánh song song bộ 4 thiết kế và tích hợp tính năng xuất tệp in vector/seamless HD cùng nhãn "AI Heritage Passport".  
* **Giai đoạn 4 (Tuần 10 – Tuần 12): Đánh giá tổng thể & Thử nghiệm thực địa**  
* Chạy toàn bộ hệ thống đánh giá tự động WiScore và SAS trên 6 nhóm hiện vật gốm.  
* Tổ chức hội đồng khảo sát người dùng thực tế với chuyên gia và làng nghề Bát Tràng.  
* Triển khai phiên bản thử nghiệm tại bảo tàng/không gian di sản số.

##### 6.2. Phân Tích & Quản Lý Rủi Ro Kỹ Thuật

Rủi Ro Kỹ Thuật,Mức Độ,Nguyên Nhân,Giải Pháp Khắc Phục Dự Phòng  
Tràn bộ nhớ GPU (OOM) khi chạy Seamless HD,Trung bình,Phân giải  \$1024 \\times 1024\$  kết hợp Noise Rolling gây tăng tải VRAM,"Sử dụng  Tiled Diffusion  phân chia mảng ẩn nhỏ ( \$64 \\times 64\$  latent tiles) để xử lý tuần tự, giữ VRAM  \$\< 4.5\\text{ GB}\$ ."  
LoRA bị Overfitting làm mất tính đa dạng,Cao,Tập dữ liệu ảnh hoa văn cổ chưa đủ phong phú hoặc số epoch quá lớn,"Áp dụng kỹ thuật  Dropout  trên các lớp LoRA, đặt trọng số LoRA linh hoạt từ  \$0.5 \- 0.75\$  trong quá trình suy luận."  
Differential Diffusion làm mờ ranh giới hoa văn,Thấp,Mức gradient trên bản đồ  \$\\mu\$  chuyển tiếp quá đột ngột,Áp dụng thuật toán làm mịn Gaussian Blur ( \$kernel=5\$ ) lên Change Map  \$\\mu\$  trước khi đưa vào bước khử nhiễu.  
LCM LoRA giảm độ chi tiết của hoa văn cổ,Trung bình,Số bước lấy mẫu quá ít (4 bước) khiến các nét mảnh bị rứt đoạn,"Thiết lập cơ chế kép: dùng LCM (6 bước) cho chế độ xem trước ( Preview ), và chuyển sang DDIM (30 bước) khi người dùng xuất bản thiết kế cuối."  
Bản đề xuất cải tiến này cung cấp một lộ trình kỹ thuật toàn diện, biến hệ thống "Tái Sinh Di Sản Số" từ một công cụ thử nghiệm khả thi (MVP) thành một nền tảng AI sáng tạo di sản mạnh mẽ, đạt chuẩn mực quốc tế về cả mặt mỹ thuật, bảo tồn di sản và hiệu năng công nghệ.  
