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

## Modul: Mata Kuliah, Kelas & Absensi

# CLARISA
### 1. MODEL & RELASI
* **Master Mata Kuliah (`campus.mata_kuliah`):** Menyimpan kode, nama, SKS, dan dosen pengampu. Satu mata kuliah dapat dikaitkan ke Jurusan, Prodi, dan Fakultas. Ketiga field ini saling mengisi otomatis secara hierarkis (Jurusan → Prodi → Fakultas).
* **Kelas sebagai pembagian slot (`campus.kelas`):** Satu mata kuliah bisa memiliki beberapa kelas (A, B, C), masing-masing dengan jadwal, ruangan, dosen, semester, dan kuota tersendiri.
* **Sesi & Baris Absensi:** Setiap pertemuan direpresentasikan sebagai satu `campus.attendance.session` yang memiliki banyak baris `campus.attendance.line`. Masing-masing mencatat status kehadiran satu mahasiswa.
* **Inheritance Mahasiswa:** Model `campus.mahasiswa` di-extend untuk menambahkan field rekap kehadiran tanpa mengubah model inti dari modul Core.

### 2. SISTEM KUOTA KELAS (FCFS)
* Kuota dihitung otomatis dari jumlah KRS yang berstatus `submitted` atau `processed` (belum ditolak).
* Dari sana sistem menghasilkan nilai `terisi`, `sisa_kuota`, dan `is_available` secara real-time.
* Validasi bentrok jadwal antar kelas dilakukan saat mahasiswa mengambil kelas melalui KRS.

### 3. WORKFLOW ABSENSI
```
Draft  →  [Confirm]  →  Confirmed
  ↑                          |
  └──── [Set to Draft] ──────┘
```
* **Draft:** Dosen membuat sesi per pertemuan, memilih kelas, dan mengisi daftar hadir. Nama sesi digenerate otomatis (contoh: `ABS/PWB/A/P3`).
* **Generate Peserta:** Tombol ini menarik otomatis daftar mahasiswa dari KRS yang sudah disetujui dan mengisi semua baris dengan status awal `alpha`. Dosen tinggal mengubah status yang hadir.
* **Confirmed:** Sesi terkunci. Daftar hadir tidak bisa diubah dan sesi tidak bisa dihapus.
* **Set to Draft:** Membatalkan konfirmasi jika ada koreksi yang perlu dilakukan.

### 4. REKAP KEHADIRAN DI MAHASISWA
* Modul ini memperluas form mahasiswa (via View Inheritance) dengan stat button absensi dan rekap persentase kehadiran.
* Persentase dihitung otomatis dari seluruh riwayat absensi mahasiswa tersebut.
* Jika persentase kehadiran di bawah 75%, banner peringatan muncul otomatis di form mahasiswa.

### 5. KEAMANAN
* **Record Rules:** Pengguna biasa hanya melihat sesi absensi yang mereka buat sendiri. Role `Attendance Manager` dapat melihat seluruh sesi dari semua pengguna.
* **Hak Akses:** Semua model didaftarkan dengan akses penuh `1,1,1,1` (Read, Write, Create, Unlink) untuk memastikan operasi CRUD dan tombol Delete tersedia di UI.
* **Pemisahan Hak Akses UI:** Role Campus Student dan Campus Lecturer dikelompokkan dalam satu privilege sehingga satu user hanya bisa memiliki salah satu role.