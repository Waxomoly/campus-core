# SHELLA
### 1. MODEL & RELASI (Architecture & ORM)

* Modul Core (campus.mahasiswa): Merancang master data identitas mahasiswa.
* Dynamic Selection: Menggunakan library Python datetime untuk menghasilkan daftar (dropdown) Angkatan dan Semester Aktif secara otomatis tanpa hard-code.
* Class Inheritance: Meng-override campus.mahasiswa dari Core ke modul Academic untuk dihubungkan dengan Transkrip Nilai.
* Arsitektur Transkrip: Menggunakan konsep "Single Live Transcript" (1 Mahasiswa = 1 Transkrip yang terus di-update) dengan relasi One2many.
* ORM Logic (Nilai): Konversi otomatis nilai angka (0-100) menjadi huruf (A-E), bobot, dan nilai mutu menggunakan @api.depends.

### 2. WORKFLOW & BUSINESS LOGIC

* Sistem KRS Berjenjang: Alur persetujuan melalui status `Draft` $\rightarrow$ `Submitted` $\rightarrow$ `Processed`.
* Validasi Bisnis KRS (Constraints):
* Limit maksimal SKS (24 SKS).
* Cegah jadwal kelas yang bentrok.
* Sistem kuota kelas rebutan (FCFS).


* Fitur Smart Sync Transkrip (action_sync_krs):
* Menarik otomatis mata kuliah dari KRS yang berstatus `Processed`.
* Logika Dictionary untuk filter mata kuliah duplikat (saat mahasiswa mengulang kelas).
* Menambahkan data baru tanpa menghapus nilai sejarah dari semester sebelumnya.



### 3. OVERRIDE METHOD & COMPUTE LOGIC

* Override Field IPK: field IPK menggunaakn compute=True dan store=True
* Penguncian UI (Readonly): Override tersebut otomatis membuat field IPK tidak bisa diedit secara manual di layar aplikasi.
* Kalkulasi Real-time vs Sah:
* IPK: Dihitung secara real-time mengambil dari Transkrip (baik Draft maupun Approved).
* SKS & Kelulusan: Hanya mem-filter Transkrip yang sah/terkunci (`state == 'approved'`).


* Otomatisasi Kelulusan: Jika Total SKS Lulus $\ge 144$ dan IPK $\ge 2.0$, sistem otomatis mengubah status master data menjadi `Lulus`.

### 4. VIEW INHERITANCE & SECURITY

* Modifikasi Tampilan (View Inheritance): Menggunakan `<xpath>` untuk menanamkan Stat Button (jumlah Transkrip) dan tab Notebook (Riwayat Akademik) langsung ke form mahasiswa Core.
* Keamanan Database (Security): Mendaftarkan akses `1,1,1,1` (Read, Write, Create, Unlink) di file `ir.model.access.csv` untuk memunculkan tombol Action (seperti Delete).
* Pemisahan Hak Akses UI: Menggunakan atribut `groups` pada XML agar tombol "Submit KRS" hanya terlihat oleh mahasiswa, sedangkan tombol "Proses KRS" dan persetujuan nilai hanya terlihat oleh Dosen.