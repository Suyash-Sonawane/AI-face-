import gradio as gr
import os

# Put your already-generated WEBM path here
WEBM_PATH = r"C:\sem 8 project\SadTalker\examples\ref_video\WDA_AlexandriaOcasioCortez_000.webm"

def show_video():
    return os.path.abspath(WEBM_PATH)

with gr.Blocks() as demo:
    btn = gr.Button("Show WEBM")
    vid = gr.Video(format="webm")

    btn.click(show_video, outputs=vid)

demo.launch()
