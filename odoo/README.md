# SHELLA

### 1. Modul yang dibuat
* Core module (`campus.mahasiswa`): Merancang master data untuk identitas mahasiswa
* Extension module (`campus academic`): Manajemen transkrip nilai. Fitur utamanya adalah otomatisasi perhitungan IPK, akumulasi SKS, penentuan kelulusan mahasiswa, dan sinkronisasi nilai dari KRS

### 2. Model & Relasi
* campus.mahasiswa (Master Mahasiswa): One2many ke tabel transkrip.
* campus.transkrip: Many2one kembali ke Mahasiswa. Relasi ini saya berikan rule 1-to-1 menggunakan SQL Constraint agar satu mahasiswa hanya memiliki satu transkrip
* campus.transkrip.nilai: Many2one ke Transkrip dan Many2one ke MK (untuk menarik referensi SKS secara otomatis)

### 3. Workflow
Transkrip nilai memiliki workflow yang diatur oleh field state:
* Draft: Status awal saat dokumen dibuat
* Submitted: Dosen menekan tombol submit setelah memasukkan nilai (memvalidasi minimal ada 1 MK)
* Approved: Status akhir di mana transkrip disahkan oleh admin/manager academic. Saat masuk ke status ini, otomatisasi perhitungan IPK dan SKS di profil Mahasiswa baru akan berjalan

### 4. Inheritance
* Model Inheritance (_inherit = 'campus.mahasiswa') tanpa membuat tabel baru 
* Tujuannya adalah untuk menggunakan field baru (seperti IPK, Total SKS Lulus, dan Status Kelulusan) langsung ke dalam tabel mahasiswa bawaan dari modul Core, sehingga datanya terintegrasi

### 5. Override Method
Override pada 3 fungsi bawaan Odoo ORM (create, write, unlink) untuk keamanan dan otomatisasi:
* Override create di Mahasiswa: mengintervensi proses simpan awal untuk membuatkan akun login (res.users) berdasarkan email yang diinput.
* Override write dan unlink di Transkrip: men-disabled fungsi Edit dan Delete bawaan Odoo jika status dokumen sudah 'Approved'. Hal ini mencegah manipulasi nilai setelah dokumen disetujui

### 6. Business Logic
* Auto-Grading: Dosen cukup memasukkan nilai angka (0-100). Sistem otomatis mengonversinya menjadi Huruf (A-E), Bobot (4-0), Nilai Mutu, dan penentuan Lulus/Tidak Lulus
* Auto-Calculation: IPK dihitung dinamis dari Total Mutu dibagi Total SKS
* Auto-Graduation: Saat SKS mencapai minimal 144 dan IPK minimal 2.0, status mahasiswa otomatis berubah menjadi 'Lulus'
* Smart Sync: Menggunakan fungsi action_sync_krs, sistem dapat menarik mata kuliah baru dari KRS yang sudah diproses, tanpa menghapus riwayat nilai mata kuliah lama

### 7. Security
a. Access Rights (RBAC pada ir.model.access.csv)
* Mahasiswa: Diberikan hak 1,0,0,0 (hanya read). tidak bisa create, edit, atau delete transkrip.
* Manager Academic: Diberikan hak 1,1,1,1 (full access CRUD).

b. Record Rules (via XML):
* Menggunakan XML domain_force [('mahasiswa_id.user_id', '=', user.id)].
* Mahasiswa hanya bisa melihat dokumen transkrip nilai milik sendiri

c. Groups:
* Menggunakan groups pada XML untuk menyembunyikan tombol-tombol krusial. 
* Contohnya, tombol "Approve Transkrip" disembunyikan dari UI mahasiswa dan hanya bisa diklik oleh group manager academic, sehingga mencegah terjadinya salah klik atau penyalahgunaan wewenang



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

## Modul: Mata Kuliah, Kelas & Absensi
# CLARISA

### 1. MODEL & RELASI (Architecture & ORM)

* **Struktur Absensi Bertingkat:** Membangun model `campus.attendance.session` sebagai representasi satu pertemuan per kelas dan `campus.attendance.line` sebagai detail kehadiran setiap mahasiswa pada sesi tersebut.
* **Relasi Kelas dan Absensi:** Setiap sesi absensi terhubung ke satu kelas (`campus.kelas`) sehingga informasi dosen, mata kuliah, jadwal, dan peserta dapat diturunkan langsung dari data akademik yang sudah ada.
* **Integrasi dengan KRS:** Data peserta absensi diambil otomatis dari mahasiswa yang telah mengambil kelas melalui KRS yang telah disetujui, sehingga tidak diperlukan input peserta secara manual.
* **Inheritance Mahasiswa:** Model `campus.mahasiswa` diperluas untuk menyimpan informasi rekapitulasi kehadiran dan integrasi dengan modul absensi.

### 2. WORKFLOW & BUSINESS LOGIC ABSENSI

* **Workflow Absensi:** Membangun alur status `Draft → Confirmed` untuk mengontrol proses pencatatan kehadiran mahasiswa.
* **Generate Peserta Otomatis:** Sistem menghasilkan detail absensi secara otomatis berdasarkan mahasiswa yang terdaftar pada kelas melalui KRS, dengan status awal `alpha`.
* **Penamaan Sesi Otomatis:** Nama sesi absensi dibentuk otomatis berdasarkan mata kuliah, kelas, dan nomor pertemuan untuk menjaga konsistensi data.
* **Penguncian Data Setelah Konfirmasi:** Sesi yang telah berstatus `Confirmed` tidak dapat diubah maupun dihapus untuk menjaga integritas data akademik.
* **Mahasiswa Melihat Absensi** Mahasiswa bisa melihat rekap absensinya di modul mahasiswa.

### 3. OVERRIDE METHOD & COMPUTE LOGIC

* **Compute Rekap Kehadiran:** Menghitung otomatis jumlah hadir, izin, sakit, alpha, dan persentase kehadiran mahasiswa menggunakan `@api.depends`.
* **Generate Detail Absensi Otomatis:** Implementasi action untuk membentuk record `campus.attendance.line` berdasarkan peserta kelas yang valid.
* **Status Kehadiran Real-Time:** Rekap dan persentase kehadiran diperbarui otomatis setiap kali terjadi perubahan pada data absensi.
* **Override CRUD (Data Locking):** Override method `write()` dan `unlink()` untuk mencegah perubahan atau penghapusan sesi absensi yang telah dikonfirmasi.

### 4. VIEW INHERITANCE & SECURITY

* **View Inheritance Mahasiswa:** Menambahkan smart button absensi, riwayat kehadiran, rekap statistik, dan indikator persentase kehadiran pada form mahasiswa tanpa mengubah view asli modul Core.
* **Record Rules Berbasis Peran:** Mahasiswa hanya dapat melihat data absensi miliknya sendiri, sedangkan dosen hanya dapat mengakses dan mengelola absensi pada kelas yang diampunya.
* **Attendance Manager:** Pengguna dengan role Attendance Manager memiliki akses penuh terhadap seluruh data sesi dan detail absensi lintas kelas.
* **Pemisahan Hak Akses UI:** Role Campus Student dan Campus Lecturer ditempatkan dalam satu privilege sehingga pengguna hanya dapat memiliki satu peran utama. Hak pengelolaan absensi diatur melalui privilege Attendance Access yang memungkinkan dosen tertentu memperoleh akses sebagai Attendance Manager.
* **Access Control:** Hak Read, Write, Create, dan Delete diatur `ir.model.access.csv`.