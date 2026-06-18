# Custom FreeSVC A100 pipeline cho data ca sĩ chunk 5s

Bộ file này đã được nhúng trực tiếp vào repo để train FreeSVC trên server A100 40GB với data custom dạng chunk/segment 5s.

## File mới được thêm

```text
config.sh                         # chỉnh path Drive/chunk, batch size, split ratio
0_run_all.sh                      # chạy toàn bộ pipeline local/sequential
1_setup.sh                        # tạo env + cài deps + tải checkpoint cần thiết
2_download_and_sort.sh            # tải/extract chunk Drive hoặc đọc folder có sẵn, sort theo singer
3_make_splits.sh                  # tạo train/valid/test theo singer, không leak ca sĩ
4_extract_pitch.sh                # pre-extract RMVPE pitch
5_train_a100.sh                   # train/finetune trên A100 40GB
configs/config-a100-custom.yaml   # config FreeSVC riêng cho pipeline này
freesvc_tools/sort_singer.py
freesvc_tools/split_by_singer.py
freesvc_tools/verify_freesvc_dataset.py
```

## Bước 1: chỉnh `config.sh`

Nếu data đã nằm trên server hoặc mount Drive:

```bash
SOURCE_DATA_DIR="/path/to/drive/chunks_or_extracted_data"
DATA_CHUNK_IDS=()
```

Nếu cần tải chunk từ Google Drive:

```bash
SOURCE_DATA_DIR=""
CHUNK_FORMAT="rar"   # zip | rar | tar | tar.gz | tgz | 7z | plain
DATA_CHUNK_IDS=(
  "GOOGLE_DRIVE_FILE_ID_1"
  "GOOGLE_DRIVE_FILE_ID_2"
)
```

Mặc định:

```bash
LANGUAGE="other"
SAMPLE_RATE=24000
CONFIG_NAME="config-a100-custom"
TRAIN_BATCH_SIZE=16
FP16_RUN=true
```

Với tiếng Việt nên để `LANGUAGE="other"` nếu không sửa language embedding config. `config-a100-custom.yaml` đang dùng `config-online-spin`, tức SPIN + ECAPA2 online đúng hướng zero-shot.

## Bước 2: chạy

Local hoặc interactive node:

```bash
chmod +x *.sh freesvc_tools/*.py
bash 0_run_all.sh
```

Hoặc chạy từng bước:

```bash
bash 1_setup.sh
bash 2_download_and_sort.sh
bash 3_make_splits.sh
bash 4_extract_pitch.sh
bash 5_train_a100.sh
```

SLURM:

```bash
mkdir -p logs
sbatch 1_setup.sh
sbatch 2_download_and_sort.sh
sbatch 3_make_splits.sh
sbatch 4_extract_pitch.sh
sbatch 5_train_a100.sh
```

## Output dataset

Sau bước sort:

```text
dataset_custom/audio/other/<singer_name>/*.wav
```

Sau bước split:

```text
dataset_custom/all.csv
dataset_custom/train.csv
dataset_custom/valid.csv
dataset_custom/test.csv
dataset_custom/singer_splits/train_singers.txt
dataset_custom/singer_splits/valid_singers.txt
dataset_custom/singer_splits/test_singers.txt
dataset_custom/singer_stats.csv
```

CSV đúng format FreeSVC:

```text
/path/to/audio.wav|other|singer_id
```

## Zero-shot split theo singer

`3_make_splits.sh` dùng `freesvc_tools/split_by_singer.py`, đảm bảo 1 singer chỉ nằm trong đúng 1 split. Tức train/dev/test không trùng ca sĩ.

Muốn tự chỉ định singer nào vào split nào thì tạo file text, mỗi dòng một singer ID, rồi sửa trong `config.sh`:

```bash
TRAIN_SINGERS_FILE="/path/to/train_singers.txt"
VAL_SINGERS_FILE="/path/to/valid_singers.txt"
TEST_SINGERS_FILE="/path/to/test_singers.txt"
```

Nếu không chỉ định, script tự random theo `VAL_SINGER_RATIO`, `TEST_SINGER_RATIO`, và `SEED`.

## Sort singer

`SORT_SINGER_MODE` trong `config.sh`:

```bash
SORT_SINGER_MODE="auto"      # ưu tiên filename, sau đó parent folder
SORT_SINGER_MODE="filename"  # singer lấy từ tên file
SORT_SINGER_MODE="parent"    # singer lấy từ folder cha
```

Ví dụ filename parse được:

```text
Son Tung_00001.wav
Son Tung - segment_00001.wav
My Singer_chunk_012.wav
```

Ví dụ folder parse được:

```text
chunk_01/Son Tung/*.wav
chunk_02/My Singer/*.flac
```

Mặc định script convert toàn bộ audio về `24kHz mono PCM wav` bằng ffmpeg để khớp FreeSVC config. Nếu data đã đúng format và muốn copy nhanh:

```bash
COPY_ONLY=1
```

## A100 40GB note

Mặc định `TRAIN_BATCH_SIZE=16`. Nếu OOM, đổi:

```bash
TRAIN_BATCH_SIZE=8
```

Nếu còn dư VRAM, thử:

```bash
TRAIN_BATCH_SIZE=24
# hoặc 32 nếu ổn
```

Checkpoint train nằm ở:

```text
dataset_custom/checkpoints/
```
