# REPORT — Lab Day 12

> Điền **bằng lời và số liệu của chính bạn** (lấy từ màn hình và từ `evidence/*.json`). Mỗi câu 4–8 dòng là đủ. Số không có trong bằng chứng của bạn sẽ bị trừ điểm. Báo cáo công khai trên GitHub; giảng viên đối chiếu với `evidence/` và với bài của các bạn khác.

| | |
|---|---|
| Họ và tên | `Tạ Hoàng Vinh` |
| MSSV (đúng bằng `--student-id` bạn đã chạy) | `202602543` |
| GitHub | `nguoibian863-ai` |
| Seed chia dữ liệu / seed mô hình (xem `evidence/closedloop.json`, mục `student`) | `7095 / 3814` |
| Số seed huấn luyện bạn dùng (`--seeds`) | `5` |

## Kết quả cuối

Điền từ `evidence/closedloop.json`, `openloop.json`, `gate.json` (cho mỗi mô hình học, lấy **dải qua các seed**).

| Bộ điều khiển | L2 vòng hở (m) | Va chạm vòng kín trên log (%) | Quyết định cổng |
|---|---|---|---|
| constant-velocity | 1.294 | 20.26 | BLOCK |
| IDM | 1.533 | 0.00 | (baseline) |
| EgoMLP | 0.764 .. 0.778 | 14.67 .. 35.17 | BLOCK |
| PercMLP | 0.622 .. 0.626 | 0.31 .. 0.83 | BLOCK |
| PercMLP+ (sau khi sửa) | 0.817 | 0.07 .. 0.14 | RELEASE |

## Câu 1 · Dữ liệu
Bước 0 bạn phát hiện những vấn đề gì ở dữ liệu? Vì sao không dùng cột `Acc_LV`, và bạn thay bằng gì? Bao nhiêu quỹ đạo bị loại vì trùng, và vì sao chia theo quỹ đạo?

Ở Bước 0 (`evidence/data_audit.json`), qua kiểm tra kiểm toán trên 992,679 dòng dữ liệu thô, tôi phát hiện ba vấn đề then chốt:
1. Cột gia tốc xe dẫn ghi nhận `Acc_LV` bị nhiễu cảm biến rất nặng và không phản ánh đúng động học thực tế: hệ số tương quan tuyến tính giữa `Acc_LV` và đạo hàm vận tốc d(speed)/dt (`acc_lead_column_corr_with_dv_dt`) chỉ đạt xấp xỉ 0.0454 (gần như bằng 0), trong khi đối với xe theo sau `acc_follower_column_corr_with_dv_dt` đạt 0.9291. Do đó, cột `Acc_LV` hoàn toàn không sử dụng được để nhận diện các pha phanh. Tôi thay thế bằng gia tốc suy dẫn `logs.a_lead`, được tính bằng đạo hàm vận tốc xe dẫn sau khi đã làm mượt đa thức qua bộ lọc (`v_lead_s`).
2. Dữ liệu thô chứa các quỹ đạo trùng lặp nguyên vẹn nhưng lại mang các ID cách xa nhau: có đúng 383 quỹ đạo trùng lặp tuyệt đối đã được phát hiện và loại bỏ, đưa tổng số quỹ đạo từ 9,993 thô xuống còn 9,610 quỹ đạo sạch (`trajectories_clean = 9610`).
3. Ta bắt buộc phải phân chia tập train/test theo từng **quỹ đạo** (trajectory level: 7,000 train / 2,610 test theo seed 7095) thay vì chia ngẫu nhiên theo khung hình (frame level). Các khung hình trong cùng một chuỗi thời gian có tương quan nội tại (temporal correlation) cực lớn; chia theo khung hình sẽ khiến khung t nằm ở train còn khung t+1 nằm ở test, gây rò rỉ dữ liệu (data leakage) nghiêm trọng và khiến điểm đánh giá vòng hở bị thổi phồng giả tạo. Đồng thời, việc loại bỏ 383 quỹ đạo trùng lặp trước khi chia giúp đảm bảo không có bản sao nào của tập train bị lọt sang tập test.

## Câu 2 · Phát lại
Bản refactor float32 khác bit ở bao nhiêu đoạn, vượt dung sai ở bao nhiêu? Thay đổi AEB làm lệch bao nhiêu đoạn, và vì sao lệch ở đúng những khung đó (mở một đoạn ra xem)? Phát theo thời gian thật làm lộ ra điều gì mà phát nhanh nhất che đi?

Từ số liệu phát lại trên 600 đoạn log (`evidence/replay.json`):
1. Bản refactor (chuyển đổi tính toán sang kiểu `float32` và thay đổi thứ tự phép toán trong công thức IDM) có đúng 600/600 đoạn khác biệt từng bit (`not_bit_identical: 600`), nhưng có 0/600 đoạn vượt quá dung sai cho phép (`differ_beyond_tol: 0`, với dung sai `atol = 1e-3, rtol = 1e-3`), độ lệch tuyệt đối lớn nhất chỉ đạt `max_abs_diff = 2.52e-5` m/s². Phép cộng số thực dấu phẩy động không có tính kết hợp: kiểm chứng demo cho thấy `(0.1 + 0.2) + 0.3 = 0.6000000000000001` trong khi `0.1 + (0.2 + 0.3) = 0.6`, và phép cộng 50,000 số float32 xuôi và ngược lệch nhau tương đối `6.94e-6`. Vì vậy, đòi hỏi bằng nhau từng bit là phi lý trong kiểm thử xe tự hành; kiểm thử có dung sai vật lý mới là tiêu chí khoa học.
2. Khi bổ sung tính năng phanh khẩn cấp AEB (`aeb_ttc = 1.5` s), chỉ có 7/600 đoạn bị thay đổi hành vi vượt dung sai (`differ_beyond_tol: 7`, gồm các đoạn: 150, 195, 208, 222, 320, 334, 560), độ lệch lớn nhất là 1.84 m/s². Khi kiểm tra chi tiết đoạn 150, AEB chỉ can thiệp ở đúng các khung hình nguy cấp khi thời gian va chạm $TTC = \text{gap} / \text{closing} < 1.5$ s, kích hoạt mức phanh khẩn cấp -6.0 m/s² thay cho lệnh phanh mềm hơn của IDM thông thường; ở tất cả các khung hình an toàn khác ($TTC \ge 1.5$ s), lệnh điều khiển giữ nguyên hoàn toàn.
3. Ở chế độ phát nhanh nhất (`fastest`), các tin nhắn được xử lý ngay lập tức mà không xét đến độ trễ hệ thống, dẫn đến 0 khung trễ và 0 khung rớt (`late: 0, dropped: 0`). Ngược lại, ở chế độ thời gian thực (`realtime`), khi mô phỏng thời gian tính toán thực tế có hiện tượng đột biến (latency spike), hệ thống làm lộ ra 582 khung bị trễ (`late: 582`) và 574 khung bị rớt (`dropped: 574`) trên tổng số 59,632 khung, khiến 371/600 đoạn bị thay đổi lệnh điều khiển với sai lệch cực đại lên tới 7.48 m/s². Chế độ phát nhanh nhất đã che giấu hoàn toàn rủi ro vi phạm thời hạn thực thi (deadline miss) — nguyên nhân có thể dẫn đến va chạm chết người trong thực tế.

## Câu 3 · Kịch bản
Lưới của bạn (tốc độ cruise, giới hạn khoảng cách, số ô): bao nhiêu % ô **không ai tránh được**? Độ trễ phản ứng 0 → 0,6 s làm vùng đâm của IDM tăng bao nhiêu? Log có phủ vùng khó không? (dẫn giới hạn phanh mạnh nhất của người lái trong log, và phần lưới đòi hỏi hơn thế)

Từ kết quả phân tích kịch bản cắt vào trên lưới 2D (`evidence/scenarios.json`):
1. Lưới kịch bản của tôi được xác định bởi tốc độ hành trình `v_ego = 10.0` m/s, dải khoảng cách từ 2.76 m đến 59.31 m (60 mốc) và tốc độ tiến gần $dv$ từ 0.0 m/s đến 10.0 m/s (45 mốc), tạo thành 2,700 ô kịch bản (`grid_cells: 2700`).
2. Khi không có độ trễ phản ứng ($t_{\text{react}} = 0.0$ s), biên vật lý bất khả thi (`unavoidable`) chiếm 0.96% diện tích lưới (26 ô). Khi tính đến độ trễ phản ứng cơ cấu chấp hành $t_{\text{react}} = 0.6$ s, diện tích bất khả thi vật lý tăng vọt lên 5.15% (139 ô). Bộ mô phỏng kiểm chứng với bộ điều khiển phanh kịch sàn `FullBrake` cho kết quả va chạm trùng khớp 100% với biên giải tích vật lý: đúng 0 ô sai lệch ở cả hai mức trễ (`mismatch_cells_away_from_frontier = 0`).
3. Đối với IDM: ở $t_{\text{react}} = 0.0$ s, tỷ lệ va chạm là 0.96% (diện tích va chạm do lỗi bộ điều khiển `attributable_area = 0.0%`). Khi tăng trễ $0.0 \to 0.6$ s, diện tích va chạm của IDM tăng từ 0.96% lên 5.15% (tăng thêm 4.19 điểm phần trăm), và diện tích do lỗi vẫn bằng đúng 0.0%! Như vậy, 100% các ca va chạm của IDM đều là va chạm bất khả kháng theo quy luật vật lý động học, không phải do thuật toán lái sai.
4. Về mức độ bao phủ của log: giới hạn phanh mạnh nhất của 99.9% người lái con người trong log (`human_brake_limit_p99.9`) chỉ đạt 3.62 m/s², trong khi cơ cấu phanh xe có thể đạt tới $B_{\text{max}} = 9.0$ m/s². Có tới 5.22% diện tích lưới kịch bản đòi hỏi mức giảm tốc vượt quá ngưỡng phanh mạnh nhất của con người trong log (`share_beyond_human_brake_limit = 5.22%`). 614 sự kiện xe dẫn phanh được khai thác từ log (`mined_events: 614`, chiếm 6.39% quỹ đạo) chủ yếu phân bố ở vùng phanh êm dịu (trung vị giảm tốc là -2.53 m/s², phân vị 1% là -4.21 m/s²). Log thực tế hoàn toàn thiếu vắng các kịch bản xe tạt đầu nguy hiểm ở cự ly gần và tốc độ cao.

## Câu 4 · Vòng hở và vòng kín
Dán bảng L2 và tỷ lệ va chạm của bốn bộ điều khiển (kèm hạng ở mỗi cách chấm). Cặp nào đổi thứ tự? Vì sao IDM có L2 như vậy mà vẫn lái tốt? Vì sao EgoMLP có L2 tốt hơn constant-velocity mà vẫn đâm?

Bảng kết quả đối chiếu giữa đánh giá vòng hở và vòng kín (`evidence/closedloop.json`):

| Bộ điều khiển | L2 vòng hở (m) | Hạng L2 | Va chạm vòng kín (%) | Hạng vòng kín |
|---|---|---|---|---|
| PercMLP | 0.625 m | 1 | 0.54% (tệ nhất: 0.83%) | 2 |
| EgoMLP | 0.769 m | 2 | 22.34% (tệ nhất: 35.17%) | 4 |
| const-vel | 1.294 m | 3 | 20.26% | 3 |
| IDM | 1.533 m | 4 | 0.00% | 1 |

Có tới 4 cặp bộ điều khiển bị đảo lộn thứ tự hoàn toàn (`order_flips`):
1. `(const-vel, IDM)`: Vòng hở const-vel tốt hơn IDM (1.294 m vs 1.533 m, hạng 3 vs 4), nhưng vòng kín IDM lái an toàn tuyệt đối 0.0% va chạm trong khi const-vel đâm 20.26%.
2. `(const-vel, EgoMLP)`: Vòng hở EgoMLP vượt trội const-vel (0.769 m vs 1.294 m), nhưng vòng kín EgoMLP đâm nhiều hơn const-vel (22.34% vs 20.26%, tệ nhất lên tới 35.17%).
3. `(IDM, EgoMLP)`: Vòng hở EgoMLP đứng nhì (0.769 m) còn IDM đứng cuối (1.533 m), nhưng vòng kín IDM đạt hạng 1 (0.0%) còn EgoMLP rớt xuống hạng bét (22.34%).
4. `(IDM, PercMLP)`: Vòng hở PercMLP vô địch (0.625 m) còn IDM kém nhất (1.533 m), nhưng vòng kín IDM dẫn đầu (0.0%) còn PercMLP xếp thứ hai (0.54%).

Giải thích cơ chế:
- IDM bị điểm L2 vòng hở kém (1.533 m) vì nó là mô hình quy tắc động học mẫu mực, không khớp từng chi tiết vi mô với phong cách lái của từng tài xế cụ thể trong log. Nhưng trong vòng kín, IDM sở hữu cơ chế phản hồi kín (closed-loop feedback) với độ ổn định tiệm cận: cự ly càng ngắn thì phản ứng phanh càng gia tăng, ngăn chặn triệt để mọi va chạm (0.0%).
- EgoMLP đạt L2 vòng hở rất tốt (0.769 m) vì nó học cách khớp trơn tru profile vận tốc quá khứ của chính nó. Tuy nhiên, nó bị "mù" hoàn toàn về nhận thức: không nhìn thấy khoảng cách `gap` và vận tốc xe dẫn `v_lead`. Khi xe dẫn phanh gấp trong vòng kín, EgoMLP không có bất kỳ thông tin nào để phản ứng cho tới khi va chạm xảy ra (tỷ lệ va chạm trên lát cắt xe dẫn phanh lên tới 65.31%, k=128/196). Ngoài ra, các sai số dự báo nhỏ của nó tích lũy dần theo từng bước thời gian (compounding execution errors), khiến xe trôi lệch khỏi quỹ đạo an toàn mà không có khả năng tự sửa lỗi.

## Câu 5 · Một lần chạy chưa đủ
EgoMLP dao động bao nhiêu giữa các seed? Khoảng tin cậy Wilson nói gì? Nếu bạn chỉ chạy đúng một seed thì có thể báo kết quả nào, và vì sao điều đó nguy hiểm?

Từ kết quả phân tích 5 seed huấn luyện ngẫu nhiên của EgoMLP (`evidence/closedloop.json`):
1. Tỷ lệ va chạm vòng kín của EgoMLP dao động dữ dội qua các seed:
   - Seed 3814: 14.67% (423/2883)
   - Seed 3818: 15.85% (457/2883)
   - Seed 3816: 21.54% (621/2883)
   - Seed 3817: 24.49% (706/2883)
   - Seed 3815: 35.17% (1014/2883)
   Dải biến động giữa seed tốt nhất (14.67%) và seed xấu nhất (35.17%) lên tới 20.50 điểm phần trăm. Tỷ lệ va chạm của seed tệ nhất cao gấp 2.4 lần so với seed tốt nhất!
2. Khoảng tin cậy Wilson 95%:
   - Seed tốt nhất (3814): [13.43%, 16.01%]
   - Seed xấu nhất (3815): [33.45%, 36.93%]
   Hai khoảng tin cậy này hoàn toàn tách rời nhau (disjoint), không hề có điểm chung. Điều này chứng minh sự chênh lệch hiệu năng không phải do nhiễu mẫu ngẫu nhiên khi kiểm thử, mà xuất phát từ tính bất định cố hữu của quá trình tối ưu phi lồi (khởi tạo trọng số ngẫu nhiên hội tụ về các cực tiểu cục bộ có chất lượng điều khiển hoàn toàn khác biệt).
3. Rủi ro chết người của việc chỉ báo cáo một seed:
   Nếu kỹ sư chỉ chạy một lần duy nhất và ngẫu nhiên chọn trúng seed 3814, họ sẽ lạc quan công bố rằng EgoMLP vượt trội hơn hẳn baseline constant-velocity (14.67% vs 20.26%). Nhưng trong thực tế, một lần huấn luyện lại trên xe có thể rơi vào seed 3815 với tỷ lệ va chạm kinh hoàng 35.17% (đâm gấp 1.7 lần cả constant-velocity). Việc kết luận dựa trên một seed tạo ra ảo tưởng an toàn nguy hiểm, che giấu sự bất ổn định của mô hình học sâu và vi phạm quy chuẩn đánh giá an toàn nghiêm ngặt của xe tự hành.

## Câu 6 · Tác nhân phản ứng
Dán bảng "xe sau phát lại" và "xe sau phản ứng". `T` bạn hiệu chỉnh là bao nhiêu, xe sau chân thực đến mức nào so với xe không phản ứng? Vì sao IDM bị tính "va chạm giả" khi xe sau chỉ phát lại, và điều này làm đổi kết luận về bộ điều khiển ra sao?

Bảng so sánh từ `evidence/agents.json` ở độ trễ phản ứng thực tế $t_{\text{react}} = 0.6$ s (tỷ lệ diện tích lưới ghi nhận va chạm bất kỳ — phía trước hoặc phía sau):

| Bộ điều khiển | Xe sau phát lại (`replay`) | Xe sau phản ứng (`reactive`) | Va chạm đuôi (replay / reactive) |
|---|---|---|---|
| const-vel | 73.37% | 73.37% | 0.00% / 0.00% |
| IDM | 70.07% | 5.15% | 64.93% / 0.00% |
| EgoMLP | 74.56% | 74.56% | 0.00% / 0.00% |
| PercMLP | 75.19% | 17.33% | 58.26% / 0.00% |
| PercMLP+ | 69.85% | 5.26% | 64.59% / 0.00% |

1. Hiệu chỉnh tham số $T$:
   Thời khoảng cách tối ưu được hiệu chỉnh là $T = 1.4$ s, cho khoảng cách Wasserstein 1-D giữa phân bố khoảng cách của mô hình và con người là $W1 = 0.3446$ (trong khi trung vị khoảng cách của người lái trong log là 1.86 s). Một tác nhân không phản ứng (chạy câm điếc) có độ lệch $W1 = 0.8486$. Như vậy mô hình xe sau phản ứng theo IDM với $T = 1.4$ s giảm độ sai lệch phân bố tới 59.4%, mô phỏng chân thực hành vi người lái bình thường.
2. Cơ chế "va chạm giả" và sự đảo ngược kết luận:
   Khi xe sau chỉ "phát lại" log (`replay`), nó hoàn toàn không biết xe thử nghiệm (ego) vừa phanh gấp để tránh xe cắt đầu phía trước. Xe sau tiếp tục lao thẳng theo tốc độ cũ và tông vào đuôi xe thử nghiệm, tạo ra tới 64.93% diện tích lưới bị va chạm phía sau đối với IDM! Trên bảng tổng sắp thế giới phát lại, IDM trông rất tệ hại với 70.07% va chạm, suýt soát bằng constant-velocity (73.37%).
   Tuy nhiên, khi đưa vào thế giới xe sau có phản ứng (`reactive`), người lái phía sau nhận biết khoảng cách thu hẹp và đạp phanh: 100% va chạm từ phía sau biến mất (về 0.00%), tổng va chạm của IDM tụt dốc từ 70.07% xuống đúng mức sàn bất khả thi vật lý là 5.15%!
   Thí nghiệm này chứng minh rằng môi trường mô phỏng không tương tác (non-reactive replay) sẽ trừng phạt bất công các bộ điều khiển biết phanh an toàn. Muốn đánh giá đúng năng lực điều khiển, thế giới mô phỏng bắt buộc phải có các tác nhân biết phản ứng.

## Câu 7 · Cổng phát hành và sửa
Quy tắc nào chặn PercMLP và nguyên nhân gốc là gì (dẫn số)? Bạn sửa bằng gì và vì sao nó chữa đúng nguyên nhân? Sau khi qua cổng, PercMLP+ có **tốt hơn** IDM không? Nó có nên được phát hành không, và bạn đề xuất làm gì trước khi quyết định?

Từ kết quả kiểm tra cổng phát hành (`evidence/gate.json`):
1. PercMLP bị CHẶN (`BLOCK`) bởi 3 quy tắc:
   - `R2_closed_loop_logs` (thất bại): Cận trên khoảng tin cậy 95% của tỷ lệ va chạm trên log ở seed tệ nhất là 1.24%, vượt quá ngưỡng không-kém-hơn baseline IDM (0.00% + 1.00% = 1.00%). Nguyên nhân gốc: sai số tích lũy (compounding errors) trong điều khiển vòng kín, do mô hình chỉ học bắt chước trạng thái con người trong log mà không biết tự sửa sai khi chệch quỹ đạo.
   - `R4_scenario_grid` (thất bại): Diện tích va chạm tránh được trên lưới kịch bản cắt vào ($t_{\text{react}} = 0.6$ s) lên tới 12.19%, vượt xa ngưỡng cho phép (baseline 0.00% + 2.00% = 2.00%). Nguyên nhân gốc: lệch phân bố dữ liệu (out-of-distribution) — log Argoverse hầu như chỉ có xe chạy nối đuôi bình thường, không chứa tình huống xe khác tạt đầu ở cự ly gần với tốc độ chênh lệch lớn.
   - `R6_reactive_world` (thất bại): Diện tích va chạm trong thế giới phản ứng là 17.33%, vượt ngưỡng baseline (5.15% + 2.00% = 7.15%) do va chạm phía trước trên lưới kịch bản còn quá cao.
2. Phương pháp sửa chữa và tính hiệu quả:
   Ta áp dụng hai giải pháp kết hợp:
   - Thêm 197,270 cửa sổ huấn luyện từ họ kịch bản cắt vào mô phỏng (`cutin_windows`), gán nhãn bằng quyết định của IDM. Điều này giải quyết tận gốc nguyên nhân thiếu dữ liệu kịch bản hiếm (OOD).
   - Huấn luyện theo thuật toán DAgger 2 vòng (`dagger_windows`): cho chính mô hình tự lái trên log, ghi lại các trạng thái lệch chuẩn mà nó tự đi vào, rồi nhờ IDM gán nhãn dự báo 3 giây tại chính các trạng thái đó. Điều này giải quyết dứt điểm hiện tượng sai số tích lũy vòng kín.
   Sau khi sửa, PercMLP+ vượt qua xuất sắc cả 7/7 quy tắc cổng (`RELEASE`): R2 giảm xuống 0.36% (đạt), R4 giảm từ 12.19% xuống 0.11% (đạt), R6 giảm xuống 5.3% (đạt).
3. Đánh giá PercMLP+ so với IDM:
   PercMLP+ **KHÔNG HỀ TỐT HƠN** IDM. Nó chỉ đạt tiêu chuẩn "không kém hơn đáng kể" (non-inferiority) trong phạm vi các kịch bản kiểm thử quy định. Vì PercMLP+ học hoàn toàn từ nhãn của IDM (nó là học trò của IDM), trần năng lực của nó bị giới hạn bởi IDM. Minh chứng rõ rệt: khi kiểm thử ở tốc độ hành trình chưa từng thấy $v_{\text{ego}} = 20.0$ m/s (`evidence/fix.json`), IDM vẫn duy trì 0.0% va chạm tránh được, trong khi PercMLP+ bắt đầu đâm tới 2.11% diện tích lưới (`attributable_area: 0.0% .. 2.11%`).
   Không nên phát hành PercMLP+ để thay thế IDM ngay lúc này. Trước khi quyết định, cần mở rộng kiểm thử trên dải tốc độ cao hơn, bổ sung kịch bản nhiễu cảm biến nặng, và xây dựng cơ chế giám sát an toàn (safety fallback filter) bằng chính luật IDM.

## Câu 8 · Bài lab này không chứng minh được gì
Chọn **ít nhất ba** giới hạn quan trọng nhất đối với việc quyết định phát hành và giải thích vì sao mỗi cái làm kết luận của bạn kém chắc chắn. Điều gì cần làm tiếp để thu hẹp khoảng cách đến thế giới thật?

Để có cái nhìn phản biện khách quan trước quyết định phát hành hệ thống tự hành ra đường thật, ba giới hạn cốt tử của bài lab này bao gồm:
1. **Động học 1 chiều dọc thuần túy (1-D Longitudinal Simplification)**:
   Mô phỏng giả định mọi xe đều chạy trên một đường thẳng tuyệt đối. Xe cắt đầu xuất hiện tức thời ở khoảng cách `gap` mà không có quỹ đạo chuyển làn ngang (lateral motion, steering, yaw rate). Trong thực tế, xe tự hành có thể chủ động đánh lái né tránh sang làn phụ hoặc lách chướng ngại vật; ngược lại, xe khác chuyển làn dần dần gây nhiễu góc quan sát. Việc giản lược bỏ qua động học ngang và đánh lái làm cho kết luận an toàn thiếu đi một nửa bài toán điều khiển xe.
2. **Nhận thức hoàn hảo và bỏ qua môi trường thực tế (Idealized Perception & Sensors)**:
   Mô hình được cung cấp trực tiếp các đại lượng vật lý hoàn hảo (`gap`, `v_lead`) với nhiễu Gauss cực nhỏ. Trong thực tế, hệ thống nhận thức (Camera/LiDAR/Radar) phải đối mặt với điều kiện khắc nghiệt: thời tiết xấu (mưa giông, sương mù, đường trơn giảm ma sát), ánh sáng chói lóa ngược nắng, góc khuất tầm nhìn, độ trễ nhận diện 3D và hiện tượng mất bám vật thể (track loss/false negatives). Nếu perception bị mất dấu xe dẫn trong 0.5 giây ở vận tốc 80 km/h, xe tự hành có thể đâm chết người trước khi bộ lập tuyến kịp ra lệnh phanh.
3. **Mô hình hành vi tác nhân mang tính công thức lý tưởng (Handcrafted Heuristic Traffic Agents)**:
   Xe sau và xe cắt đầu trong bài lab phản ứng tuân thủ hoàn toàn theo công thức toán học IDM với hệ số $T$ cố định. Con người ngoài đời thực có hành vi phức tạp, đa dạng và khó đoán hơn rất nhiều: tài xế có thể mất tập trung xem điện thoại, buồn ngủ, say rượu, phanh giật mình hoảng loạn hoặc cố tình tạt đầu chèn ép đối kháng (adversarial aggressive driving). Việc chỉ thử nghiệm với các tác nhân tuân thủ luật IDM không thể đảm bảo an toàn khi đối đầu với con người thực tế.

**Các bước đi tiếp theo để thu hẹp khoảng cách:**
- Nâng cấp lên bộ mô phỏng 3D đa làn hoàn chỉnh (như CARLA hoặc Highway-env) với mô hình động học xe 6 bậc tự do (6-DOF) và mô hình ma sát lốp phi tuyến tính (Pacejka).
- Tích hợp pipeline nhận thức đầy đủ từ luồng ảnh camera/point cloud LiDAR thô vào vòng lặp kiểm thử (Sensor-in-the-loop / Software-in-the-loop).
- Xây dựng các kịch bản đối kháng (adversarial scenario generation) và kiểm thử thực tế trên sa hình kín (closed proving ground) có giám sát an toàn nghiêm ngặt trước khi chạy thử nghiệm trên đường giao thông công cộng.
