# Anti-Stalling & Grace Band 80 Clarification (2026-10-18)

## 1. Su Co Hien Truong: Dung Lai Giai Trinh Khi Truot Gate
- Boi canh: Sau khi hoan tat task van hanh tren thiet bi farm, Operator phat lenh "Done" de chot phien.
- Hanh vi sai lam cua Coordinator:
  * Thay tu khoa "Done", Coordinator tu dong chay closeout_gate quet toan bo repo.
  * Reviewer cham 76-77 diem (do code cu chua push tu ca truoc).
  * Coordinator dung lai va giai trinh thu tuc voi Operator ("em bi 77 diem nen giu commit local...").
  * Operator phe phan nghiem khac ve hanh vi te liet, dong thoi chi ro mau thuan giua viec ep 85 diem rau ria vs Grace Band 80 diem thuc te.

## 2. Quy Tac Chuan Hoa Da Thong Nhat

### A. Anti-Stalling & Anti-Bureaucracy Invariant
- Lenh "Done" tu Operator la menh lenh chot viec dut khoat.
- Khi Gate chua dat diem, CAM TUYET DOI dung lai giua chung de ke le diem so hay giai trinh thu tuc voi Operator.
- Loi ky thuat chua dat la trach nhiem tu than cua Agent. Phai tu dong khac phuc trong vong lap kin hoac bao BLOCKED kem bang chung ro rang neu het ngan sach, tuyet doi khong duoc ke le trinh bay.

### B. Grace Band (80-84 Diem) & Chong Cay Diem Vun Vat
- Toan bo codebase thuc te va User Profile deu thong nhat:
  Nguong san 80 diem (Grace Band 80-84) kem Mechanical Test Xanh 100% la APPROVED va tu dong push.
- CAM TUYET DOI ep cay diem len 85 bang cach sua vun vat (sua docstring, type hints rau ria khi logic test da pass 100%). Dieu nay gay ra vong lap vo tan cua Reviewer va lang phi token.

### C. Pre-Closeout Short-Circuit Cho Task Thiet Bi
- Voi cac session thuan tuy van hanh thiet bi hoac khi target files da khop 100% remote upstream, co che pre-closeout short-circuit tu dong nhan dien va exit 0 ngay (ALREADY_PUSHED), khong kich hoat review mu quang tren toan repo.
