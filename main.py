"""
Accessible Image Captioner - Main GUI Application
A production-ready desktop tool for generating image captions with text-to-speech support.
"""

import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pyttsx3
from PIL import Image, ImageTk

# Optional drag-and-drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DRAG_DROP_AVAILABLE = True
except ImportError:
    DRAG_DROP_AVAILABLE = False

# Add utils to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.captioner import ImageCaptioner


class AccessibleImageCaptionerApp:
    """Main application class for the Accessible Image Captioner."""
    
    def __init__(self, root):
        """Initialize the application."""
        self.root = root
        self.root.title("Accessible Image Captioner")
        self.root.geometry("900x700")
        
        # Application state
        self.current_image_path = None
        self.current_caption = None
        self.captioner = None
        self.tts_engine = None
        self.high_contrast_mode = False
        
        # Initialize TTS engine
        self._init_tts()
        
        # Setup UI
        self._setup_styles()
        self._create_menu()
        self._create_widgets()
        self._setup_keyboard_shortcuts()
        
        # Load model in background
        self._load_model_async()
    
    def _init_tts(self):
        """Initialize text-to-speech engine."""
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)  # Speed
            self.tts_engine.setProperty('volume', 0.9)  # Volume
        except Exception as e:
            messagebox.showerror("TTS Error", f"Failed to initialize text-to-speech: {str(e)}")
    
    def _setup_styles(self):
        """Configure application styles and themes."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Define color schemes
        self.normal_colors = {
            'bg': '#f0f0f0',
            'fg': '#000000',
            'button_bg': '#4CAF50',
            'button_fg': '#ffffff',
            'frame_bg': '#ffffff'
        }
        
        self.high_contrast_colors = {
            'bg': '#000000',
            'fg': '#FFFF00',
            'button_bg': '#FFFF00',
            'button_fg': '#000000',
            'frame_bg': '#1a1a1a'
        }
        
        self._apply_color_scheme(self.normal_colors)
    
    def _apply_color_scheme(self, colors):
        """Apply color scheme to the application."""
        self.root.configure(bg=colors['bg'])
        
        style = ttk.Style()
        style.configure('TFrame', background=colors['bg'])
        style.configure('TLabel', background=colors['bg'], foreground=colors['fg'], font=('Arial', 12))
        style.configure('Title.TLabel', font=('Arial', 18, 'bold'))
        style.configure('Caption.TLabel', font=('Arial', 14), wraplength=700)
        style.configure('TButton', font=('Arial', 12, 'bold'), padding=10)
    
    def _create_menu(self):
        """Create application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Image (Ctrl+O)", command=self.select_image)
        file_menu.add_command(label="Export Caption (Ctrl+S)", command=self.export_caption)
        file_menu.add_separator()
        file_menu.add_command(label="Exit (Ctrl+Q)", command=self.root.quit)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle High Contrast (Ctrl+H)", command=self.toggle_high_contrast)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
    
    def _create_widgets(self):
        """Create and layout all UI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="Accessible Image Captioner",
            style='Title.TLabel'
        )
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Loading model, please wait...")
        self.status_label.grid(row=1, column=0, pady=(0, 10))
        
        # Image display frame
        image_frame = ttk.Frame(main_frame, relief=tk.SUNKEN, borderwidth=2)
        image_frame.grid(row=2, column=0, pady=(0, 20), sticky=(tk.W, tk.E))
        
        drag_drop_text = "\n\nDrag & drop an image here or click 'Select Image'" if DRAG_DROP_AVAILABLE else "\n\nClick 'Select Image' to begin"
        
        self.image_label = ttk.Label(
            image_frame,
            text=f"No image selected{drag_drop_text}",
            anchor=tk.CENTER,
            justify=tk.CENTER
        )
        self.image_label.pack(pady=50, padx=50)
        
        # Enable drag and drop (if tkinterdnd2 is available)
        if DRAG_DROP_AVAILABLE:
            try:
                self.image_label.drop_target_register(DND_FILES)
                self.image_label.dnd_bind('<<Drop>>', self._on_drop)
            except Exception as e:
                print(f"Drag-and-drop initialization failed: {e}")
        
        # Caption display
        caption_frame = ttk.Frame(main_frame)
        caption_frame.grid(row=3, column=0, pady=(0, 20), sticky=(tk.W, tk.E))
        
        ttk.Label(caption_frame, text="Generated Caption:", font=('Arial', 12, 'bold')).pack(anchor=tk.W)
        
        self.caption_text = tk.Text(
            caption_frame,
            height=4,
            width=80,
            font=('Arial', 14),
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief=tk.SOLID,
            borderwidth=1
        )
        self.caption_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, pady=(0, 10))
        
        # Create buttons with keyboard navigation
        self.select_btn = tk.Button(
            button_frame,
            text="Select Image (Ctrl+O)",
            command=self.select_image,
            bg='#2196F3',
            fg='white',
            font=('Arial', 12, 'bold'),
            padx=20,
            pady=10,
            cursor='hand2'
        )
        self.select_btn.grid(row=0, column=0, padx=5)
        
        self.generate_btn = tk.Button(
            button_frame,
            text="Generate Caption (Ctrl+G)",
            command=self.generate_caption,
            bg='#4CAF50',
            fg='white',
            font=('Arial', 12, 'bold'),
            padx=20,
            pady=10,
            cursor='hand2',
            state=tk.DISABLED
        )
        self.generate_btn.grid(row=0, column=1, padx=5)
        
        self.read_btn = tk.Button(
            button_frame,
            text="Read Aloud (Ctrl+R)",
            command=self.read_aloud,
            bg='#FF9800',
            fg='white',
            font=('Arial', 12, 'bold'),
            padx=20,
            pady=10,
            cursor='hand2',
            state=tk.DISABLED
        )
        self.read_btn.grid(row=0, column=2, padx=5)
        
        self.export_btn = tk.Button(
            button_frame,
            text="Export Alt-Text (Ctrl+S)",
            command=self.export_caption,
            bg='#9C27B0',
            fg='white',
            font=('Arial', 12, 'bold'),
            padx=20,
            pady=10,
            cursor='hand2',
            state=tk.DISABLED
        )
        self.export_btn.grid(row=0, column=3, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for accessibility."""
        self.root.bind('<Control-o>', lambda e: self.select_image())
        self.root.bind('<Control-O>', lambda e: self.select_image())
        self.root.bind('<Control-g>', lambda e: self.generate_caption())
        self.root.bind('<Control-G>', lambda e: self.generate_caption())
        self.root.bind('<Control-r>', lambda e: self.read_aloud())
        self.root.bind('<Control-R>', lambda e: self.read_aloud())
        self.root.bind('<Control-s>', lambda e: self.export_caption())
        self.root.bind('<Control-S>', lambda e: self.export_caption())
        self.root.bind('<Control-h>', lambda e: self.toggle_high_contrast())
        self.root.bind('<Control-H>', lambda e: self.toggle_high_contrast())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<Control-Q>', lambda e: self.root.quit())
    
    def _load_model_async(self):
        """Load the captioning model in a background thread."""
        def load():
            try:
                self.captioner = ImageCaptioner()
                self.root.after(0, self._on_model_loaded)
            except Exception as e:
                self.root.after(0, lambda: self._on_model_error(str(e)))
        
        thread = threading.Thread(target=load, daemon=True)
        thread.start()
    
    def _on_model_loaded(self):
        """Callback when model is successfully loaded."""
        self.status_label.config(text="✓ Model loaded successfully! Select an image to begin.")
        messagebox.showinfo("Ready", "Image captioning model loaded successfully!")
    
    def _on_model_error(self, error_msg):
        """Callback when model loading fails."""
        self.status_label.config(text="✗ Failed to load model. Please restart the application.")
        messagebox.showerror("Model Error", f"Failed to load captioning model:\n{error_msg}")
    
    def select_image(self):
        """Open file dialog to select an image."""
        file_path = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self._load_image(file_path)
    
    def _on_drop(self, event):
        """Handle drag-and-drop event."""
        file_path = event.data
        # Remove curly braces if present
        file_path = file_path.strip('{}')
        
        if os.path.isfile(file_path):
            self._load_image(file_path)
    
    def _load_image(self, image_path):
        """Load and display the selected image."""
        try:
            self.current_image_path = image_path
            
            # Load and resize image for display
            img = Image.open(image_path)
            img.thumbnail((600, 400), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img)
            
            # Update image label
            self.image_label.config(image=photo, text="")
            self.image_label.image = photo  # Keep a reference
            
            # Enable generate button
            if self.captioner:
                self.generate_btn.config(state=tk.NORMAL)
            
            # Update status
            filename = Path(image_path).name
            self.status_label.config(text=f"Image loaded: {filename}")
            
            # Clear previous caption
            self.caption_text.config(state=tk.NORMAL)
            self.caption_text.delete(1.0, tk.END)
            self.caption_text.config(state=tk.DISABLED)
            self.current_caption = None
            self.read_btn.config(state=tk.DISABLED)
            self.export_btn.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image:\n{str(e)}")
    
    def generate_caption(self):
        """Generate caption for the current image."""
        if not self.current_image_path:
            messagebox.showwarning("No Image", "Please select an image first.")
            return
        
        if not self.captioner:
            messagebox.showwarning("Model Not Ready", "Please wait for the model to load.")
            return
        
        # Disable buttons and start progress
        self.generate_btn.config(state=tk.DISABLED)
        self.progress.start()
        self.status_label.config(text="Generating caption...")
        
        def generate():
            try:
                caption = self.captioner.generate_caption(self.current_image_path)
                self.root.after(0, lambda: self._on_caption_generated(caption))
            except Exception as e:
                self.root.after(0, lambda: self._on_caption_error(str(e)))
        
        thread = threading.Thread(target=generate, daemon=True)
        thread.start()
    
    def _on_caption_generated(self, caption):
        """Callback when caption is successfully generated."""
        self.progress.stop()
        self.generate_btn.config(state=tk.NORMAL)
        
        if caption:
            self.current_caption = caption
            
            # Display caption
            self.caption_text.config(state=tk.NORMAL)
            self.caption_text.delete(1.0, tk.END)
            self.caption_text.insert(1.0, caption)
            self.caption_text.config(state=tk.DISABLED)
            
            # Enable read and export buttons
            self.read_btn.config(state=tk.NORMAL)
            self.export_btn.config(state=tk.NORMAL)
            
            self.status_label.config(text="✓ Caption generated successfully!")
            
            # Automatically read aloud for accessibility
            self.read_aloud()
        else:
            self._on_caption_error("Failed to generate caption")
    
    def _on_caption_error(self, error_msg):
        """Callback when caption generation fails."""
        self.progress.stop()
        self.generate_btn.config(state=tk.NORMAL)
        self.status_label.config(text="✗ Caption generation failed")
        messagebox.showerror("Error", f"Caption generation failed:\n{error_msg}")
    
    def read_aloud(self):
        """Read the current caption aloud using TTS."""
        if not self.current_caption:
            messagebox.showwarning("No Caption", "Please generate a caption first.")
            return
        
        if not self.tts_engine:
            messagebox.showerror("TTS Error", "Text-to-speech engine is not available.")
            return
        
        def speak():
            try:
                self.tts_engine.say(self.current_caption)
                self.tts_engine.runAndWait()
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("TTS Error", f"Failed to read aloud:\n{str(e)}"))
        
        thread = threading.Thread(target=speak, daemon=True)
        thread.start()
        
        self.status_label.config(text="🔊 Reading caption aloud...")
    
    def export_caption(self):
        """Export the current caption as a text file."""
        if not self.current_caption:
            messagebox.showwarning("No Caption", "Please generate a caption first.")
            return
        
        # Suggest filename based on image
        if self.current_image_path:
            suggested_name = Path(self.current_image_path).stem + "_caption.txt"
        else:
            suggested_name = "caption.txt"
        
        file_path = filedialog.asksaveasfilename(
            title="Export Caption",
            defaultextension=".txt",
            initialfile=suggested_name,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.current_caption)
                
                self.status_label.config(text=f"✓ Caption exported to {Path(file_path).name}")
                messagebox.showinfo("Success", f"Caption exported successfully to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export caption:\n{str(e)}")
    
    def toggle_high_contrast(self):
        """Toggle high contrast mode for accessibility."""
        self.high_contrast_mode = not self.high_contrast_mode
        
        if self.high_contrast_mode:
            colors = self.high_contrast_colors
            self.status_label.config(text="High contrast mode enabled")
        else:
            colors = self.normal_colors
            self.status_label.config(text="Normal mode enabled")
        
        self._apply_color_scheme(colors)
        
        # Update text widget colors
        if self.high_contrast_mode:
            self.caption_text.config(bg='#000000', fg='#FFFF00')
        else:
            self.caption_text.config(bg='#FFFFFF', fg='#000000')
    
    def _show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About",
            "Accessible Image Captioner v1.0\n\n"
            "An offline desktop tool for generating image captions with text-to-speech support.\n\n"
            "Model: nlpconnect/vit-gpt2-image-captioning\n"
            "Powered by Hugging Face Transformers & PyTorch"
        )
    
    def _show_shortcuts(self):
        """Show keyboard shortcuts dialog."""
        shortcuts = (
            "Keyboard Shortcuts:\n\n"
            "Ctrl+O - Select Image\n"
            "Ctrl+G - Generate Caption\n"
            "Ctrl+R - Read Aloud\n"
            "Ctrl+S - Export Caption\n"
            "Ctrl+H - Toggle High Contrast\n"
            "Ctrl+Q - Quit Application"
        )
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)


def main():
    """Main entry point for the application."""
    if DRAG_DROP_AVAILABLE:
        try:
            root = TkinterDnD.Tk()
        except Exception as e:
            print(f"TkinterDnD initialization failed: {e}")
            root = tk.Tk()
    else:
        root = tk.Tk()
    
    app = AccessibleImageCaptionerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
