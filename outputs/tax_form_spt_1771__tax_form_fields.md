# Extraction result

## Page 1

| Line | Field | Value | Status | Source |
|---|---|---|---|---|
| NPWP | NPWP | 12.345.678.9-000.000 | ok | 📍 p.1 · "NPWP 12 345 678 9 000 000" |
| NAMA WAJIB PAJAK | NAMA WAJIB PAJAK | PT ABC EFG | ok | 📍 p.1 · "NAMA WAJIB PAJAK PT ABC EFG" |
| JENIS USAHA | JENIS USAHA | PERDAGANGAN | ok | 📍 p.1 · "JENIS USAHA PERDAGANGAN" |
| NO. TELEPON | NO. TELEPON | XXX-XXXXXXXXX | ❓ unreadable (Value is masked with X) | 📍 p.1 · "NO. TELEPON XXX - XXXXXXXXX" |
| PERIODE PEMBUKUAN | PERIODE PEMBUKUAN | 2020 s.d. 2021 | ok | 📍 p.1 · "PERIODE PEMBUKUAN 2020 s.d. 2021" |

- [x] TIDAK DIAUDIT 
  📍 p.1 · "TIDAK DIAUDIT"

| Line | Field | Value | Status | Source |
|---|---|---|---|---|
| 1 | PENGHASILAN NETO FISKAL | Rp62.628.902 | ok | 📍 p.1 · "1 PENGHASILAN NETO FISKAL Rp62.628.902" |
| 2 | KOMPENSASI KERUGIAN FISKAL | Rp20.000.000 | ok | 📍 p.1 · "2 KOMPENSASI KERUGIAN FISKAL Rp20.000.000" |
| 3 | PENGHASILAN KENA PAJAK | Rp42.628.902 | ok | 📍 p.1 · "3 PENGHASILAN KENA PAJAK Rp42.628.902" |

- [x] 4c Tarif PPh Ps. 31E ayat (1)
  📍 p.1 · "Tarif PPh Ps. 31E ayat (1)"

| Line | Field | Value | Status | Source |
|---|---|---|---|---|
| 4 | PPh TERUTANG | Rp2.500.100 | ok | 📍 p.1 · "4 Rp2.500.100" |
| 6 | JUMLAH PPh TERUTANG | Rp2.500.100 | ok | 📍 p.1 · "6 JUMLAH PPh TERUTANG Rp2.500.100" |
| 7 | PPh DITANGGUNG PEMERINTAH | Rp0 | ok | 📍 p.1 · "7 PPh DITANGGUNG PEMERINTAH Rp0" |
| 8a | KREDIT PAJAK DALAM NEGERI | Rp600.000 | ok | 📍 p.1 · "8a KREDIT PAJAK DALAM NEGERI Rp600.000" |
| 8b | KREDIT PAJAK LUAR NEGERI | Rp0 | ok | 📍 p.1 · "8b KREDIT PAJAK LUAR NEGERI Rp0" |
| 8c | JUMLAH | Rp600.000 | ok | 📍 p.1 · "8c JUMLAH Rp600.000" |

- [x] 9 PPh YANG HARUS DIBAYAR SENDIRI
  📍 p.1 · "9 PPh YANG HARUS DIBAYAR SENDIRI"

| Line | Field | Value | Status | Source |
|---|---|---|---|---|
| 9 | PPh YANG HARUS DIBAYAR SENDIRI | Rp1.900.100 | ok | 📍 p.1 · "9 PPh YANG HARUS DIBAYAR SENDIRI Rp1.900.100" |
| 10a | PPh Ps. 25 BULANAN | Rp0 | ok | 📍 p.1 · "10a PPh Ps. 25 BULANAN Rp0" |
| 10b | STP PPh Ps. 25 | Rp0 | ok | 📍 p.1 · "10b STP PPh Ps. 25 Rp0" |
| 10c | JUMLAH | Rp0 | ok | 📍 p.1 · "10c JUMLAH Rp0" |
| 11a | PPh YANG KURANG DIBAYAR | Rp1.900.100 | ok | 📍 p.1 · "11a PPh YANG KURANG DIBAYAR Rp1.900.100" |
| 12 | PPh YANG KURANG DIBAYAR PADA ANGKA 11.a DISETOR TANGGAL | 30 04 2022 | ok | 📍 p.1 · "12 PPh YANG KURANG DIBAYAR PADA ANGKA 11.a DISETOR TANGGAL 30 04 2022" |

## Validation issues

- **info** (p.None, 11): Check 11 = 9 - 10c skipped: a value is missing or unreadable.

## Run info

- provider: gemini
- model: gemini-3.1-flash-lite
- pages: 1
- total time: 5.9s
- tokens (in/out): 1500 / 2126
- provider calls: 1
- cache hits: 0
- coverage: 100%
- grounded evidence: n/a
- arithmetic checks: 3/4
- failed pages: none
