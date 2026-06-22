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

# REYHAN
### 1. MODEL & RELASI (Architecture & ORM)

* Master Data Akademik: Membangun seluruh master data inti di `campus_core` (Mahasiswa, Dosen, Mata Kuliah, Kelas) sebagai fondasi seluruh sistem.
* Hirarki Struktur Kampus: Merancang relasi berjenjang Fakultas $\rightarrow$ Prodi $\rightarrow$ Jurusan, dengan `fakultas_id` pada Jurusan di-related otomatis dari Prodi agar hirarki saling terhubung.
* Dynamic Selection: Dropdown Angkatan & Semester Aktif di-generate otomatis dari tahun berjalan (library Python datetime) tanpa hard-code, beserta default semester berjalan.
* Relasi Dua Arah Dosen ↔ Mata Kuliah: Many2many memakai relasi yang sama persis (`campus_mk_dosen_rel`) sehingga "Dosen Pengampu" dan "Mata Kuliah Diampu" konsisten dua arah.
* Master Data Organisasi: Membangun seluruh master data `campus_hr` (Tipe Organisasi, Jabatan, Jabatan Kepanitiaan, Divisi) sebagai acuan fitur Organisasi.

### 2. WORKFLOW & BUSINESS LOGIC

* Fondasi Sistem KRS/Enrollment: Membangun inti `campus.krs` — lembar KRS per mahasiswa per semester beserta baris mata kuliahnya.
* Validasi Bisnis KRS (Constraints):
* Limit maksimal SKS (24 SKS).
* Cegah jadwal kelas yang bentrok (`is_bentrok_with`).
* Sistem kuota kelas rebutan (FCFS).
* Hanya mahasiswa berstatus `Aktif` yang boleh mengisi KRS, dan 1 mata kuliah = 1 kelas.
* Workflow KRS Berjenjang: Alur Student ↔ Lecturer melalui status `Draft` $\rightarrow$ `Submitted` $\rightarrow$ `Processed`.
* Fondasi Transkrip Nilai: Membangun awal `campus.transkrip` (1 Mahasiswa = 1 Transkrip) beserta konversi nilai angka (0-100) menjadi huruf, bobot, dan nilai mutu.
* Fitur Organisasi (keseluruhan): Membangun penuh modul `campus_hr` — Data Organisasi, Proposal Kegiatan, dan Kepanitiaan.
* Penomoran Proposal Otomatis: Menghasilkan nomor resmi format `001/NVSTLK/HIMA/PCU/VI/2026` (ambil konsonan judul + bulan Romawi + nomor urut otomatis).
* Aturan BPH Kepanitiaan: Divisi BPH hanya boleh diisi jabatan BPH, divalidasi real-time (onchange) sekaligus lewat constraint.

### 3. OVERRIDE METHOD & COMPUTE LOGIC

* Compute Logic: Menghitung otomatis jumlah prodi/jurusan, jumlah anggota & proposal organisasi, serta kuota kelas (`terisi`, `sisa_kuota`, `is_available`) menggunakan @api.depends.
* Override CRUD (Penguncian Data): Override `create`/`write`/`unlink` agar Proposal & Transkrip yang sudah `Approved` tidak bisa diubah/dihapus, serta menolak proposal dari organisasi non-aktif.
* Auto-isi Cakupan Akademik: Onchange pada Mata Kuliah — memilih Jurusan otomatis mengisi Prodi & Fakultas ke atas.

### 4. VIEW INHERITANCE & SECURITY

* View & Menu: Menyusun seluruh form/list master data akademik beserta menu sidebar (Master Data, KRS, Organisasi, Proposal Kegiatan).
* Report PDF (QWeb): Membuat cetak Proposal Kegiatan menjadi dokumen PDF.
* Keamanan Database (Record Rule): Mahasiswa hanya melihat proposal miliknya sendiri, sedangkan Lecturer melihat semua (`rule_proposal_own` vs `rule_proposal_manager`).
* Pemisahan Hak Akses: Hak akses CRUD per model dibedakan untuk Student vs Lecturer di file `ir.model.access.csv`.