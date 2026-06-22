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