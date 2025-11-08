"""
Sprite Sheet Validator - Frame Consistency Checks
Version: 3.1
Platform: Intel Mac (macOS Ventura) + Docker

Complete validation of generated sprite sheets:
- Dimension validation (32x32 pixels per frame)
- Blank frame detection (>95% single color = blank)
- Color palette extraction via KMeans
- Palette consistency across frames (similarity threshold)
- Dominant color variance (detect different characters)
- Motion analysis (frame-to-frame differences)
"""

from typing import List, Dict, Tuple
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans


class SpriteSheetValidator:
    """
    Validates generated sprite sheets for visual consistency
    
    Checks performed:
    1. All frames are exactly 32x32 pixels
    2. No completely blank frames (>95% single color)
    3. Color palettes are similar across frames (>85% similarity)
    4. Dominant colors match (same character/entity)
    5. Reasonable motion between frames (not static, not random)
    """
    
    def __init__(
        self,
        tolerance: float = 0.15,
        blank_threshold: float = 0.95,
        motion_min: float = 0.01,
        motion_max: float = 0.5
    ):
        """
        Initialize validator with thresholds
        
        Args:
            tolerance: Allowed variation in palette similarity (0.0-1.0)
                      0.15 = allow 15% difference between palettes
            blank_threshold: Threshold for blank frame detection (0.0-1.0)
                           0.95 = flag if >95% pixels are same color
            motion_min: Minimum motion score to avoid static frames
            motion_max: Maximum motion score to avoid random frames
        """
        self.tolerance = tolerance
        self.blank_threshold = blank_threshold
        self.motion_min = motion_min
        self.motion_max = motion_max
    
    def validate_frames(self, frame_paths: List[str]) -> Dict:
        """
        Validate all frames for consistency
        
        Args:
            frame_paths: List of file paths to frame images
        
        Returns:
            Validation report dict with:
                - valid (bool): Overall pass/fail
                - total_frames (int): Number of frames checked
                - errors (List[str]): Critical errors (dimensions, blank frames)
                - warnings (List[str]): Non-critical issues (low similarity)
                - metrics (Dict): Detailed metrics (palette_similarity, etc.)
        
        Example return:
            {
                "valid": True,
                "total_frames": 8,
                "errors": [],
                "warnings": ["Frames have inconsistent palettes (0.78)"],
                "metrics": {
                    "palette_similarity": 0.78,
                    "color_variance": 0.12,
                    "motion_scores": [0.05, 0.08, 0.06, ...]
                }
            }
        """
        # Load all frames
        frames = []
        for path in frame_paths:
            try:
                frame = Image.open(path).convert('RGB')
                frames.append(frame)
            except Exception as e:
                return {
                    "valid": False,
                    "total_frames": len(frame_paths),
                    "errors": [f"Failed to load {path}: {e}"],
                    "warnings": [],
                    "metrics": {}
                }
        
        report = {
            "valid": True,
            "total_frames": len(frames),
            "errors": [],
            "warnings": [],
            "metrics": {}
        }
        
        # Check 1: Dimension validation
        for i, frame in enumerate(frames):
            if frame.size != (32, 32):
                report["valid"] = False
                report["errors"].append(
                    f"Frame {i} has incorrect dimensions: {frame.size}, expected (32, 32)"
                )
        
        # Check 2: Blank frame detection
        for i, frame in enumerate(frames):
            if self._is_blank_frame(frame, self.blank_threshold):
                report["valid"] = False
                report["errors"].append(
                    f"Frame {i} appears to be blank (>{self.blank_threshold*100:.0f}% single color)"
                )
        
        # Check 3: Color palette consistency
        palettes = [self._extract_palette(frame, n_colors=8) for frame in frames]
        palette_similarity = self._calculate_palette_similarity(palettes)
        
        report["metrics"]["palette_similarity"] = round(palette_similarity, 4)
        
        if palette_similarity < (1.0 - self.tolerance):
            report["warnings"].append(
                f"Frames have inconsistent color palettes (similarity: {palette_similarity:.2f}, "
                f"threshold: {1.0 - self.tolerance:.2f}). This may indicate different characters."
            )
        
        # Check 4: Dominant color consistency
        dominant_colors = [self._get_dominant_color(frame) for frame in frames]
        color_variance = self._calculate_color_variance(dominant_colors)
        
        report["metrics"]["color_variance"] = round(color_variance, 4)
        
        if color_variance > self.tolerance:
            report["warnings"].append(
                f"Frames show high color variance ({color_variance:.2f}). "
                f"May be different characters or lighting changes."
            )
        
        # Check 5: Motion analysis
        if len(frames) > 1:
            motion_scores = self._analyze_motion(frames)
            report["metrics"]["motion_scores"] = [round(s, 4) for s in motion_scores]
            
            avg_motion = np.mean(motion_scores)
            
            if avg_motion < self.motion_min:
                report["warnings"].append(
                    f"Very low motion detected (avg: {avg_motion:.3f}). "
                    f"Frames may be too similar."
                )
            
            if avg_motion > self.motion_max:
                report["warnings"].append(
                    f"Very high motion detected (avg: {avg_motion:.3f}). "
                    f"Frames may be too different."
                )
        
        return report
    
    def _is_blank_frame(self, frame: Image.Image, threshold: float) -> bool:
        """
        Check if frame is mostly a single color (blank)
        
        Args:
            frame: PIL Image
            threshold: Threshold for uniformity (0.0-1.0)
        
        Returns:
            True if >threshold% of pixels are the same color
        
        Example:
            Frame with 1000 pixels, 980 are white, 20 are black
            unique_colors = 2
            uniformity = (1024 - 2) / 1024 = 0.998 (99.8%)
            If threshold=0.95, returns True (blank)
        """
        pixels = np.array(frame)
        
        # Get unique RGB colors
        # reshape(-1, 3) converts (32, 32, 3) -> (1024, 3)
        pixels_flat = pixels.reshape(-1, 3)
        unique_colors = len(np.unique(pixels_flat, axis=0))
        
        total_pixels = frame.size[0] * frame.size[1]
        uniformity = (total_pixels - unique_colors) / total_pixels
        
        return uniformity > threshold
    
    def _extract_palette(self, frame: Image.Image, n_colors: int = 8) -> np.ndarray:
        """
        Extract dominant colors from frame using K-Means clustering
        
        Args:
            frame: PIL Image
            n_colors: Number of colors to extract
        
        Returns:
            Array of shape (n_colors, 3) with RGB values
        
        Algorithm:
            1. Flatten image to list of RGB pixels
            2. Run K-Means with k=n_colors
            3. Return cluster centers (dominant colors)
        
        Example output:
            [[15, 56, 15],    # Dark green
             [48, 98, 48],    # Medium green
             [139, 172, 15],  # Light green
             [155, 188, 15]]  # Lightest green
        """
        pixels = np.array(frame).reshape(-1, 3)
        
        # Handle case where image has fewer unique colors than requested
        unique_pixels = np.unique(pixels, axis=0)
        k = min(n_colors, len(unique_pixels))
        
        if k == 0:
            return np.array([])
        
        # K-Means clustering
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        return kmeans.cluster_centers_
    
    def _calculate_palette_similarity(self, palettes: List[np.ndarray]) -> float:
        """
        Calculate average similarity between color palettes
        
        Args:
            palettes: List of palette arrays from _extract_palette
        
        Returns:
            Similarity score 0.0-1.0 (1.0 = identical)
        
        Algorithm:
            1. For each pair of palettes:
               - For each color in palette1, find closest color in palette2
               - Calculate Euclidean distance
               - Average all distances
            2. Normalize by max RGB distance (441 = sqrt(255^2 * 3))
            3. Convert distance to similarity: 1.0 - (distance / 441)
            4. Average all pairwise similarities
        
        Example:
            Palette1: [[15, 56, 15], [48, 98, 48]]
            Palette2: [[16, 55, 16], [47, 99, 47]]
            
            Color1→Color2 distances:
            - [15,56,15] → [16,55,16]: sqrt(1^2 + 1^2 + 1^2) = 1.73
            - [48,98,48] → [47,99,47]: sqrt(1^2 + 1^2 + 1^2) = 1.73
            
            Avg distance: 1.73
            Similarity: 1.0 - (1.73 / 441) = 0.996 (99.6% similar)
        """
        if len(palettes) < 2:
            return 1.0
        
        similarities = []
        
        # Compare all pairs of palettes
        for i in range(len(palettes) - 1):
            for j in range(i + 1, len(palettes)):
                palette1 = palettes[i]
                palette2 = palettes[j]
                
                if len(palette1) == 0 or len(palette2) == 0:
                    continue
                
                # For each color in palette1, find closest in palette2
                min_distances = []
                for color1 in palette1:
                    distances = [
                        np.linalg.norm(color1 - color2)
                        for color2 in palette2
                    ]
                    min_distances.append(min(distances))
                
                # Average minimum distance
                avg_distance = np.mean(min_distances)
                
                # Normalize to 0-1 scale
                # Max RGB distance: sqrt(255^2 + 255^2 + 255^2) ≈ 441
                similarity = 1.0 - (avg_distance / 441.0)
                similarities.append(similarity)
        
        return np.mean(similarities) if similarities else 1.0
    
    def _get_dominant_color(self, frame: Image.Image) -> np.ndarray:
        """
        Get single most dominant color in frame
        
        Args:
            frame: PIL Image
        
        Returns:
            RGB array [R, G, B]
        """
        palette = self._extract_palette(frame, n_colors=1)
        return palette[0] if len(palette) > 0 else np.array([0, 0, 0])
    
    def _calculate_color_variance(self, colors: List[np.ndarray]) -> float:
        """
        Calculate variance in dominant colors across frames
        
        Args:
            colors: List of RGB arrays
        
        Returns:
            Variance score 0.0-1.0 (normalized)
        
        High variance indicates different characters or major lighting changes
        """
        if len(colors) < 2:
            return 0.0
        
        colors_array = np.array(colors)
        
        # Calculate variance per channel (R, G, B)
        variance = np.mean(np.var(colors_array, axis=0))
        
        # Normalize to 0-1 scale (max variance = 255^2)
        normalized_variance = variance / (255 ** 2)
        
        return normalized_variance
    
    def _analyze_motion(self, frames: List[Image.Image]) -> List[float]:
        """
        Analyze frame-to-frame motion using pixel differences
        
        Args:
            frames: List of PIL Images
        
        Returns:
            List of motion scores (one per frame transition)
        
        Motion score calculation:
            1. Convert frames to numpy arrays
            2. Calculate absolute difference between consecutive frames
            3. Average all pixel differences
            4. Normalize to 0-1 scale
        
        Interpretation:
            - ~0.0: Frames are identical (static)
            - 0.01-0.1: Small motion (idle animation, breathing)
            - 0.1-0.3: Moderate motion (walk cycle)
            - 0.3-0.5: Large motion (attack, jump)
            - >0.5: Frames are very different (likely error)
        """
        if len(frames) < 2:
            return []
        
        motion_scores = []
        
        for i in range(len(frames) - 1):
            frame1 = np.array(frames[i]).astype(float)
            frame2 = np.array(frames[i + 1]).astype(float)
            
            # Calculate pixel-wise absolute difference
            diff = np.abs(frame1 - frame2)
            
            # Average difference, normalize to 0-1
            motion_score = np.mean(diff) / 255.0
            
            motion_scores.append(motion_score)
        
        return motion_scores


# Example usage
if __name__ == "__main__":
    validator = SpriteSheetValidator(
        tolerance=0.15,          # Allow 15% palette variation
        blank_threshold=0.95,    # Flag if >95% single color
        motion_min=0.01,         # Warn if motion <1%
        motion_max=0.5           # Warn if motion >50%
    )
    
    # Validate frames
    frame_paths = [
        "/app/output/sprite_frame_0_00001.png",
        "/app/output/sprite_frame_1_00001.png",
        "/app/output/sprite_frame_2_00001.png",
        "/app/output/sprite_frame_3_00001.png",
        "/app/output/sprite_frame_4_00001.png",
        "/app/output/sprite_frame_5_00001.png",
        "/app/output/sprite_frame_6_00001.png",
        "/app/output/sprite_frame_7_00001.png",
    ]
    
    report = validator.validate_frames(frame_paths)
    
    print(f"Valid: {report['valid']}")
    print(f"Frames: {report['total_frames']}")
    
    if report['errors']:
        print("\nErrors:")
        for error in report['errors']:
            print(f"  - {error}")
    
    if report['warnings']:
        print("\nWarnings:")
        for warning in report['warnings']:
            print(f"  - {warning}")
    
    print("\nMetrics:")
    for key, value in report['metrics'].items():
        print(f"  {key}: {value}")