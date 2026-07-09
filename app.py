"""app.py — Phase 6: Gradio UI for the full Video Generation Pipeline.

This app sits at the root of the project and imports the orchestration pipeline.
"""
import os
import gradio as gr
from orchestration.orchestrator import orchestrate_video
from tts.voice_store import list_voice_ids

DEFAULT_BACKEND = os.environ.get("BACKEND_URL", "")


def build_ui():
    """Builds and returns the Gradio UI blocks."""
    voices = list_voice_ids()
    default_voice = voices[0] if voices else "default"

    with gr.Blocks(title="VibeVoice Video Pipeline", css="footer {visibility: hidden}") as demo:
        gr.Markdown("# VibeVoice End-to-End Video Generator")
        gr.Markdown(
            "This pipeline generates a fully synced and captioned video from a text script. "
            "It runs through TTS (Colab GPU or CPU fallback), Forced Alignment, LLM Storyboarding, "
            "and Remotion rendering."
        )

        with gr.Tabs():
            with gr.Tab("Generate Video"):
                with gr.Row():
                    with gr.Column():
                        script_input = gr.Textbox(
                            label="Video Script",
                            lines=6,
                            placeholder="Enter the text you want the avatar to speak...",
                            value="Welcome to the VibeVoice pipeline! We are generating a video with perfect lip sync."
                        )
                        voice_dropdown = gr.Dropdown(
                            choices=voices,
                            value=default_voice,
                            label="Voice Identity"
                        )
                        format_radio = gr.Radio(
                            choices=["16:9", "9:16"],
                            value="16:9",
                            label="Video Format (YouTube vs Reels/Shorts)"
                        )
                        backend_url = gr.Textbox(
                            label="Colab TTS Backend URL (Optional)",
                            value=DEFAULT_BACKEND,
                            placeholder="https://xxxxx.gradio.live — leave blank to use local CPU"
                        )
                        generate_btn = gr.Button("Generate Video", variant="primary")

                    with gr.Column():
                        status_output = gr.Textbox(label="Pipeline Status", interactive=False)
                        video_output = gr.Video(label="Generated Video")

                # Connect the generator function to the UI button
                generate_btn.click(
                    fn=orchestrate_video,
                    inputs=[script_input, voice_dropdown, backend_url, format_radio],
                    outputs=[status_output, video_output],
                )

            with gr.Tab("Clone Voice"):
                gr.Markdown("Upload a short 5-15s clear audio clip to clone a new voice.")
                with gr.Row():
                    with gr.Column():
                        clone_name = gr.Textbox(label="New Voice Name", placeholder="e.g. my-custom-voice")
                        clone_audio = gr.Audio(type="filepath", label="Reference Audio")
                        clone_btn = gr.Button("Clone Voice")
                    with gr.Column():
                        clone_status = gr.Textbox(label="Status", interactive=False)
                
                def _do_clone(name, path):
                    if not name or not path:
                        return "Error: Name and audio required", gr.update()
                    from tts.voice_store import register_voice
                    try:
                        register_voice(name, path)
                        new_voices = list_voice_ids()
                        return f"Success! '{name}' is ready to use.", gr.update(choices=new_voices, value=name)
                    except Exception as e:
                        return f"Error: {e}", gr.update()

                clone_btn.click(
                    fn=_do_clone,
                    inputs=[clone_name, clone_audio],
                    outputs=[clone_status, voice_dropdown]
                )

    return demo


if __name__ == "__main__":
    app = build_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        share=os.environ.get("GRADIO_SHARE") == "1",
    )
