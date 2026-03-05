# SadTalker：Learning Realistic 3D Motion Coefficients for Stylized Audio-Driven Single Image Talking Face Animation

<img src='https://user-images.githubusercontent.com/4397546/229853431-1c7614ff-59d8-4d5c-8c53-559c7b800ffd.png' width='500px'>

<a href='https://arxiv.org/abs/2211.12194'><img src='https://img.shields.io/badge/ArXiv-2211.12194-red'></a> 
<a href='https://sadtalker.github.io'><img src='https://img.shields.io/badge/Project-Page-green'></a>
<a href='https://huggingface.co/spaces/vinthony/SadTalker'><img src='https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue'></a> 
<a href='https://www.youtube.com/watch?v=9U0N4GkhGZo'><img src='https://img.shields.io/badge/YouTube-red'></a>


<p align="center">
  <img src="https://user-images.githubusercontent.com/4397546/222494788-b6a322c8-63eb-4196-8007-59f3d227dc46.gif" alt="character picture" width="400px">
</p>

<!-- ## Highlight --> 

### Network Architecture
<img src='https://user-images.githubusercontent.com/4397546/229267545-22a5bc45-528e-4209-bd08-eab681a8c0de.png' width='1000px'>

## Installation

### Requirements
- Python 3.8+
- PyTorch 1.10+
- GPU with CUDA 11.3+

### Install from scratch
```bash
# Clone the repo
git clone https://github.com/OpenTalker/SadTalker.git
cd SadTalker

# Create conda environment (optional)
conda create -n sadtalker python=3.8
conda activate sadtalker

# Install dependencies
pip install -r requirements.txt

# Download models
bash scripts/download_models.sh
```

## Usage

### WebUI
```bash
python app.py
```

### Command Line
```bash
python inference.py --driven_audio <audio.wav> --source_image <image.png> --result_dir <output_dir>
```

## Citation
```bibtex
@article{zhang2022sadtalker,
  title={SadTalker: Learning Realistic 3D Motion Coefficients for Stylized Audio-Driven Single Image Talking Face Animation},
  author={Zhang, Wenxuan and Cun, Xiaodong and Wang, Yong and Zhang, Xi and Shen, Yongqiang and Guo, Yu and Zhao, Ying and Zhang, Jingdong},
  journal={arXiv preprint arXiv:2211.12194},
  year={2022}
}
```

## License
This project is licensed under the MIT License.
