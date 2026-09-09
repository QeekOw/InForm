# InForm — Brief UI/UX Frontend

Dokumen serah-terima untuk desainer UI. Isinya: apa itu InForm, frontend ini untuk siapa,
satu ide utama yang wajib tersampaikan lewat desain, dan peta layar per layar yang perlu
didesain. Nama field dan contoh angka di sini adalah **angka asli dari produk** — tolong
pakai itu, jangan placeholder.

> Terjemahan dari `frontend-ui-brief.md` (commit `c55d8ec`). Versi Inggris adalah acuan
> utama; kalau versi itu berubah, berkas ini perlu ikut diperbarui.

---

## 1. Apa itu InForm

InForm membaca hasil scan komposisi tubuh InBody (lembar hasil cetak dari alat scan di gym
atau klinik) lalu mengubahnya jadi rencana harian yang konkret: berapa kalori dan berapa gram
protein, karbohidrat, lemak, dan serat yang perlu dimakan, plus latihan yang menargetkan
ketidakseimbangan otot kiri/kanan orang tersebut.

Alur yang dilalui pengguna:

1. Mengisi beberapa data diri (usia, jenis kelamin, tingkat aktivitas, tujuan).
2. Memberikan lembar InBody miliknya.
3. Sistem membaca angka-angka di lembar itu secara otomatis (ini tahap OCR, dan **ini bagian
   yang paling ingin kami tonjolkan**).
4. Sistem menghitung target dan mendeteksi ketidakseimbangan otot.
5. Sistem menampilkan rencana yang sudah jadi dan mudah dibaca.

## 2. Untuk siapa dan untuk apa

- **Tujuan:** karya portofolio. Sasarannya membuat sisi engineering terlihat sangat rapi di
  mata yang melihat (recruiter, reviewer, kolaborator). Ini **bukan** produk medis yang
  dipakai sungguhan, jadi tidak ada pembayaran dan tidak ada halaman settings.
  Tapi **ada akun**, karena ide kedua produk ini adalah **progres dari waktu ke waktu**:
  kamu scan lagi beberapa bulan kemudian dan melihat apa yang berubah.
- **Satu akun, satu orang.** Pemilik akun adalah orang yang di-scan. Tidak ada mode
  pelatih-dengan-klien, tidak ada ganti-ganti orang.
- **Platform:** **web app**, didesain **mobile-first**, dan ditampilkan di dalam
  **frame ponsel** (mockup HP di halaman). Rasanya harus seperti aplikasi HP, tapi jalan di
  browser lewat satu link. Prioritaskan layar selebar ponsel; tampilan desktop yang rapi itu
  bonus, bukan prioritas.
- **Penekanan:** **momen pembacaan scan (OCR)** adalah bintang utama seluruh pengalaman ini.
  Penjelasannya di bawah.

## 3. Satu ide yang wajib tersampaikan lewat desain

Kebanyakan aplikasi "AI fitness" menampilkan angka tanpa kamu tahu angka itu datang dari mana.
InForm dibangun dengan prinsip sebaliknya. **Setiap angka dihitung oleh kode yang sederhana
dan bisa diaudit, langsung dari lembar scan. AI hanya menulis kalimat di sekitar angka itu,
dan tidak pernah boleh mengubahnya.**

Desain harus membuat sifat *bisa dipercaya* itu **terlihat**. Dua ide praktis (silakan
dikembangkan lebih jauh):

- **Tunjukkan buktinya.** Saat lembar dibaca, tampilkan lembar scan dan angka hasil ekstraksi
  berdampingan, supaya orang bisa melihat bahwa angka di rencana itu berasal dari angka di
  lembar. Momen "mesin membaca ini, dan inilah persis yang dia lihat" adalah bagian yang perlu
  didramatisasi.
- **Dua suara visual.** Angka-angka keras (kalori, makro, persentase ketidakseimbangan) harus
  terasa presisi, eksak, buatan mesin. Paragraf coaching (satu-satunya bagian yang ditulis AI)
  boleh terasa lebih lembut dan manusiawi. Membedakan keduanya secara visual memperkuat inti
  produk ini.

## 3b. Dua aturan yang harus dihormati desain

Ini bukan detail teknis; ini mengubah apa yang boleh dan tidak boleh dilakukan tiap layar.

- **Satu scan dibekukan selamanya.** Satu scan = lembar yang dibaca + empat data diri orang itu
  **pada saat itu** + rencana yang dihasilkan. Tidak pernah diedit. Scan lagi berarti
  **menambah** scan baru, bukan menimpa yang lama. Jadi tidak ada tombol "edit rencana ini" di
  mana pun, dan setiap rencana lama tetap persis seperti saat dihitung.
- **Empat data diri itu menempel pada scan, bukan pada akun.** Kalau seseorang mengubah
  tujuannya dari menurunkan lemak menjadi menambah massa otot, rencana-rencana lamanya tetap
  memakai tujuan yang dipakai saat itu. Akun hanya mengingat jawaban terakhir untuk mengisi
  otomatis formulir berikutnya. Inilah alasan riwayat bisa dipercaya sebagai catatan.

## 4. Nada dan arah visual

Terbuka untuk desainer, tapi ada beberapa rambu:

- Ini produk kesehatan dan komposisi tubuh, jadi rasanya harus **bersih, presisi, dan tenang**
  — lebih dekat ke alat medis atau alat data yang bagus, bukan aplikasi fitness konsumer yang
  ramai. Kepercayaan di atas hype.
- Angka adalah konten utama. Tipografi dan layout untuk **data yang mudah dibaca** (pasangan
  angka/label yang jelas, hierarki yang baik) lebih penting daripada ilustrasi.
- Karena pembacaan scan adalah bintangnya, ada ruang untuk satu momen yang benar-benar berkesan
  di tahap "membaca lembar" (animasi, efek scan, reveal). Habiskan budget visual di sana.

## 5. Layar yang perlu didesain (cetak biru)

Intinya alur pendek dan linear. Tolong desain tiap layar untuk lebar ponsel, termasuk state
loading dan error-nya bila disebutkan.

### Layar 0 — Masuk / buat akun
- Tujuan: membawa orang masuk ke akunnya.
- Buat seringan mungkin: ini karya pameran, dan formulir pendaftaran yang berat adalah cara
  tercepat kehilangan pengunjung. Desain versi paling minimal yang masih masuk akal.
- State yang perlu didesain: belum masuk, dan kasus error (data salah).
- Catatan: pengunjung harus bisa **melihat** InForm itu apa sebelum diminta masuk. Desain
  Layar 1 supaya bisa diakses tanpa login.

### Layar 1 — Intro / mulai
- Tujuan: menjelaskan InForm dalam satu kalimat, lalu memulai alur.
- Isi: nama produk, penjelasan satu kalimat, satu tombol utama ("Mulai" atau semacamnya).
  Opsional: ringkasan kecil "cara kerjanya" dalam 4 langkah.
- Buat singkat. Ini pintu masuk, bukan landing page marketing.

### Layar 2 — Tentang kamu (formulir data diri)
- Tujuan: mengumpulkan empat data diri yang dibutuhkan.
- Field (ini persis, tolong dipakai apa adanya):
  - **Age** (usia) — angka.
  - **Biological sex** (jenis kelamin biologis) — dua pilihan: **male** / **female**.
  - **Activity level** (tingkat aktivitas) — satu pilihan dari lima tingkat. Tampilkan label
    yang ramah; masing-masing dipetakan ke angka di balik layar:
    - Sedentary (1.2)
    - Lightly active (1.375)
    - Moderately active (1.55)
    - Very active (1.725)
    - Extremely active (1.9)
  - **Goal** (tujuan) — dua pilihan: **Fat loss** dan **Build muscle** (di sistem:
    "fat_loss" dan "hypertrophy").
- Desain kontrol input-nya (stepper, tombol segmented, selector) untuk ponsel.

### Layar 3 — Berikan lembar scan-mu
- Tujuan: pengguna memberi lembar InBody untuk dibaca.
- **Pemilih lembar contoh adalah jalur utama.** Galeri berisi lembar InBody yang kami
  sediakan. Sebagian sintetis, sebagian hasil cetak asli yang kami punya izinnya, dan galeri
  harus **menyebutkan mana yang mana** — kejujuran itu bagian dari cerita kepercayaan yang
  sama seperti bagian lain di produk ini.
- **"Unggah punyamu sendiri" sekarang sudah pasti ada**, bukan wacana, tapi dirilis setelah
  jalur lembar contoh. Desain sebagai aksi sekunder yang nyata, bukan placeholder. Saat
  mengunggah perlu ada satu kalimat sederhana yang menyebut bahwa ini proyek mahasiswa, dan
  bahwa kami menyimpan angkanya tapi **tidak menyimpan fotonya**.
- **Lembar contoh dijawab dari hasil pembacaan yang sudah tersimpan.** Model kami jalankan
  lebih dulu ke seluruh galeri dan hasilnya disimpan, jadi memilih lembar contoh langsung
  memberi hasil seketika. Ada aksi sekunder **"Jalankan model secara live pada lembar ini"**
  yang benar-benar membacanya ulang, dan jalur itu memakan waktu penuh sekitar **45 detik**.
  Desain aksi live sebagai langkah kedua yang disengaja, bukan default — supaya pengunjung
  baru tidak pernah dipaksa menunggu 45 detik sebelum melihat apa pun.
- Isi: beberapa thumbnail lembar yang bisa dipilih, satu kalimat pendek yang menjelaskan
  seperti apa lembar InBody itu, dan aksi utama "Baca lembar ini".

### Layar 4 — Membaca lembar (momen bintang)
- Tujuan: memperlihatkan proses OCR berlangsung. Ini layar yang harus berkesan.
- Dua bagian:
  - **State "sedang membaca" / proses berjalan.** Lembar sedang dibaca. Di sinilah animasi
    garis scan atau reveal bertahap cocok. Harus terasa mesin benar-benar sedang menelusuri
    lembar itu. **Waktu tunggunya nyata dan lama — sekitar 45 detik** untuk foto yang
    diunggah, karena model benar-benar berjalan. Desain sesuatu yang bisa menahan perhatian
    selama itu dan menunjukkan progres secara jujur; spinner biasa akan terasa seperti rusak.
    (Lembar contoh dijawab seketika, jadi state ini paling penting untuk unggahan dan untuk
    pembacaan ulang live.)
  - **Hasil ekstraksi.** Tampilkan lembar scan berdampingan dengan angka yang berhasil
    diambil, supaya kaitannya jelas. Tolong desain tampilan satu nilai hasil ekstraksi
    (label, nilai, satuan) dan bagaimana kumpulannya terbaca sebagai satu grup.
- **Field hasil ekstraksi yang perlu ditata** (field asli dari lembar):
  - Weight (kg)
  - Lean Body Mass / Fat Free Mass (kg)
  - Percent Body Fat (%)
  - Skeletal Muscle Mass (kg)
  - Basal Metabolic Rate (kcal)
  - Visceral Fat Level (bilangan bulat kecil, bisa saja tidak ada)
  - Segmental lean, lima nilai: lengan kiri, lengan kanan, kaki kiri, kaki kanan, batang tubuh
    (masing-masing kg)
  - Source device (contoh: "InBody 570")
- **State yang perlu didesain di sini:**
  - Normal: semua field terbaca bersih.
  - **Field ditandai (flagged) / tidak terbaca (unread):** kadang sebuah nilai tidak bisa
    dibaca dengan yakin. Tolong desain tampilan satu field ketika nilainya meragukan atau
    hilang, jelas berbeda dari pembacaan yang bersih. Kejujuran soal tingkat keyakinan ini
    bagian dari cerita kepercayaan.
  - **Penolakan satu lembar penuh:** kadang tidak ada satu pun yang bisa dibaca. Ini cukup
    sering terjadi sehingga penting — pada foto lembar asli, saat ini terjadi sekitar separuh
    kasus. Ini **bukan** state error dan tidak boleh terlihat seperti aplikasi rusak: sistem
    memilih untuk tidak menebak, dan itu justru produk bekerja sesuai rancangan.

- **Di layar inilah orang mengoreksi hasil pembacaan.** Semua nilai hasil ekstraksi bisa
  diedit di sini, bersebelahan dengan lembar asalnya. Field yang tidak terbaca mesin, atau
  yang ditandai meragukan, **wajib** diisi sebelum lanjut; sisanya boleh diedit kalau orangnya
  melihat ada yang salah. Tolong desain:
  - tampilan nilai yang bisa diedit (state diam, sedang difokus, dan sudah diubah orang),
  - perlakuan "wajib diisi sebelum lanjut" untuk field unread dan flagged,
  - dan peringatan nilai di luar batas wajar, karena pasti ada yang mengetik 900 kg.

  Nilai yang diketik orang disebut **corrected field**, dan tampilannya tetap jelas berbeda
  dari nilai yang dibaca mesin — di layar ini maupun di mana pun nilai itu muncul nanti.

### Layar 5 — Angka-angkamu (target hasil perhitungan)
- Tujuan: menampilkan hasil hitungan kode dari lembar scan. Semuanya angka keras.
- **Blok nutrisi** (field persis):
  - Daily Energy Target (kcal) — angka utama
  - BMR (kcal) dan TDEE (kcal) — ditampilkan sebagai dasar pendukung
  - Protein (g)
  - Carbohydrates (g)
  - Fats (g)
  - Fiber (g)
- **Blok ketidakseimbangan:**
  - Nol, satu, atau lebih ketidakseimbangan yang terdeteksi, masing-masing satu baris singkat
    yang mudah dibaca, misalnya "Deviasi massa lean lengan kiri/kanan 11,1%". Desain juga
    kasus kosong (tidak ada ketidakseimbangan) dan kasus satu-atau-lebih.
- Layar ini harus terasa eksak dan bisa dipercaya. Ini angka-angka yang sudah diaudit.

### Layar 6 — Latihanmu
- Tujuan: menampilkan latihan yang direkomendasikan, terkait ketidakseimbangan di atas.
- Tiap item latihan punya: **nama**, **otot yang disasar**, dan **tag tipe** yang salah satu
  dari tiga: *corrective (unilateral)*, *compound (bilateral)*, atau *cardio (HIIT)*. Tolong
  desain baris latihan dan bagaimana tag tipe itu terbaca.
- Contoh baris:
  - Single-arm dumbbell row — menyasar lats — corrective (unilateral)
  - Single-arm overhead press — menyasar deltoid — corrective (unilateral)
  - Rowing sprint intervals — kardio — cardio (HIIT)
- Desain untuk daftar pendek (3 sampai 6 item).

### Layar 7 — Rencana dalam bentuk kalimat
- Tujuan: satu-satunya bagian yang ditulis AI. Paragraf coaching pendek dan hangat yang
  merangkai angka-angka itu dan menjelaskan rencananya dengan bahasa sederhana.
- Ini "suara lembut" dari bagian 3. Harus terbaca sebagai prosa, jelas berbeda secara visual
  dari blok angka. Boleh diletakkan di atas hasil sebagai pengantar, atau jadi layar penutup
  tersendiri. Penempatannya diserahkan ke desainer.

> Catatan: Layar 5, 6, dan 7 bersama-sama membentuk "hasil". Ketiganya boleh jadi satu layar
> hasil yang di-scroll, bukan tiga layar terpisah, kalau itu lebih enak dibaca di ponsel.
> Anggap saja tiga blok konten, satu tujuan.

### Layar 8 — Riwayat
- Tujuan: alasan keberadaan akun. Menampilkan scan seseorang dari waktu ke waktu.
- Isi: daftar scan lama urut dari yang terbaru. Tiap baris menampilkan tanggal plus dua atau
  tiga angka utama (saran: berat, persen lemak tubuh, target energi harian), dan bisa diketuk
  untuk membuka hasil lengkap scan tersebut.
- **State yang perlu didesain:** kasus kosong (akun baru yang belum punya scan — ini yang
  pertama dilihat kebanyakan pengunjung, jadi penting), satu scan, dan banyak scan.
- **Nilai hasil koreksi tetap terlihat di sini.** Kalau sebuah scan mengandung field yang
  diketik orang, bukan dibaca mesin, baris riwayatnya harus menunjukkan itu — badge kecil atau
  hitungan sudah cukup. Garis tren yang sebagian bersandar pada angka ketikan harus terlihat
  berbeda dari yang seluruhnya dibaca dari lembar, kalau tidak riwayatnya menyiratkan
  kepastian yang tidak dimilikinya.
- **Nilai tambah (opsional):** satu garis tren kecil (persen lemak tubuh dari waktu ke waktu)
  di atas daftar. Silakan didesain, tapi anggap fitur ini mungkin rilis setelah daftarnya.

### Layar 9 — Pengguna yang kembali / rencana kedaluwarsa
- Tujuan: apa yang dilihat orang saat kembali setelah lama tidak membuka.
- Mereka mendarat di rencana terbarunya, dengan usia rencana itu tertera jelas ("dari scan-mu
  tanggal 14 Maret"). Lewat 30 hari, tampilannya harus terbaca **kedaluwarsa**: masih sah
  sebagai catatan, tapi terlihat jelas sudah waktunya diperbarui, dengan aksi "Scan baru" yang
  menonjol.
- Desain label usia dan perlakuan "kedaluwarsa" itu. Penting: kedaluwarsa **bukan** error dan
  **bukan** peringatan. Rencana lama itu benar saat dibuat dan masih benar; dia hanya
  menggambarkan tubuh yang lebih lama.

## 6. State lintas-layar yang perlu didesain

- **Loading:** tahap pembacaan (Layar 4) punya waktu tunggu nyata saat model bekerja. Desain
  state loading yang menahan perhatian, bukan spinner polos.
- **Error / fallback:** kalau pembacaan atau pembuatan rencana gagal, produk jatuh ke rencana
  sederhana yang aman, bukan menampilkan angka yang salah. Desain state error yang tenang dan
  tidak terasa rusak.
- **Data kosong / meragukan:** kasus field flagged di Layar 4, dan kasus tanpa ketidakseimbangan
  di Layar 5.

## 7. Inventaris komponen (didesain sekali, dipakai di mana-mana)

- Pasangan angka + label + satuan (primitif data inti; muncul di mana-mana)
- Metrik utama berukuran besar (target energi harian)
- Kontrol pilihan: toggle dua opsi (jenis kelamin, tujuan), selector lima opsi (aktivitas)
- Thumbnail / pemilih lembar contoh
- Animasi pembacaan scan dan kartu nilai hasil ekstraksi
- Perlakuan nilai flagged/meragukan
- Nilai hasil ekstraksi yang bisa diedit, dan perlakuan "ini diketik orang"
- State penolakan satu lembar penuh (tenang, bukan error)
- Item baris ketidakseimbangan
- Baris latihan dengan tag tipe
- Blok prosa / naratif (suara AI)
- Tombol primer dan sekunder, indikasi progres sepanjang alur
- Frame ponsel yang membungkus seluruh aplikasi di halaman

## 8. Di luar cakupan (jangan didesain)

- Mode pelatih / trainer: mengelola scan orang lain. Satu akun satu orang.
- Mengedit atau menghapus scan atau rencana lama (scan bersifat permanen — lihat bagian 3b)
- Halaman settings, berbagi, ekspor
- Pembayaran atau langganan
- Tur onboarding di luar intro sederhana

## 9. Pertanyaan terbuka untuk desainer

1. Layar 5 sampai 7 sebaiknya satu scroll panjang atau beberapa swipe? Keputusanmu, berdasarkan
   mana yang paling enak dibaca di ponsel.
2. Seberapa literal "frame ponsel"-nya? Mockup perangkat yang realistis, atau sekadar sugesti
   ringan?
3. Paragraf tulisan AI sebaiknya di mana: membuka hasil, atau menutupnya?
4. Seberapa jauh animasi pembacaan scan didorong? Ini bintangnya, jadi mungkin cukup jauh —
   tapi tetap harus terasa presisi, bukan gimmick.
5. **Bahasa antarmuka aplikasi: Inggris atau Indonesia?** Ini belum diputuskan. Nama field di
   dokumen ini sengaja dibiarkan dalam bahasa Inggris karena itu nama sebenarnya di sistem,
   tapi label yang dilihat pengguna bisa saja berbahasa Indonesia. Tolong konfirmasi sebelum
   menulis teks antarmuka.

---

### Ringkasan satu kalimat

InForm membaca hasil scan tubuh dari gym lalu menulis rencana makan dan latihan harian yang
bisa dipercaya. Tugas desainnya: membuat alur web pendek berbentuk ponsel, di mana momen
pembacaan scan terasa mengesankan dan setiap angka terlihat jelas berasal dari lembar scan
asalnya.
