"""
Enhanced face recognition with distance and angle robustness.
Handles distorted faces from different camera angles and varying distances.
"""

import cv2
import numpy as np
import face_recognition
from typing import List, Dict, Tuple, Optional


class EnhancedFaceRecognizer:
    """
    Advanced face recognition with:
    - Multi-scale detection for distance variations
    - Face quality assessment
    - Angle-aware recognition with higher tolerance
    - Adaptive upsampling based on face size
    """

    def __init__(
        self,
        base_tolerance: float = 0.65,  # Higher tolerance for angles
        min_face_size: int = 30,       # Minimum face size in pixels
        max_upsample: int = 2,         # Maximum upsampling for distant faces
        quality_threshold: float = 0.3 # Minimum quality score
    ):
        self.base_tolerance = base_tolerance
        self.min_face_size = min_face_size
        self.max_upsample = max_upsample
        self.quality_threshold = quality_threshold

    def assess_face_quality(self, face_image: np.ndarray) -> float:
        """
        Assess face quality based on:
        - Size
        - Sharpness (Laplacian variance)
        - Brightness

        Returns quality score 0.0 to 1.0
        """
        if face_image is None or face_image.size == 0:
            return 0.0

        h, w = face_image.shape[:2]

        # Size score (0.0 to 1.0)
        face_area = h * w
        size_score = min(face_area / (100 * 100), 1.0)  # Normalize to 100x100

        # Sharpness score using Laplacian variance
        gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY) if len(face_image.shape) == 3 else face_image
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(laplacian_var / 500.0, 1.0)  # Normalize

        # Brightness score (prefer well-lit faces)
        mean_brightness = gray.mean()
        brightness_score = 1.0 - abs(mean_brightness - 128) / 128.0

        # Combined quality score
        quality = (size_score * 0.4 + sharpness_score * 0.4 + brightness_score * 0.2)

        return quality

    def calculate_adaptive_upsample(self, face_bbox: Tuple[int, int, int, int]) -> int:
        """
        Calculate optimal upsampling based on face size.
        Smaller (distant) faces get more upsampling.
        """
        top, right, bottom, left = face_bbox
        face_width = right - left
        face_height = bottom - top
        face_size = min(face_width, face_height)

        if face_size < 40:
            return self.max_upsample  # Small face, maximum upsampling
        elif face_size < 80:
            return 1  # Medium face, moderate upsampling
        else:
            return 0  # Large face, no upsampling needed

    def detect_faces_multiscale(
        self,
        image: np.ndarray,
        model: str = "hog"
    ) -> List[Dict]:
        """
        Detect faces at multiple scales for robustness.
        Tries different upsampling levels to catch distant/angled faces.
        """
        if image is None or image.size == 0:
            return []

        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if len(image.shape) == 3 else image

        all_faces = []

        # Try multiple upsampling levels
        for upsample in [0, 1, 2]:
            try:
                locations = face_recognition.face_locations(
                    rgb_image,
                    number_of_times_to_upsample=upsample,
                    model=model
                )

                if locations:
                    for loc in locations:
                        # Check if this face already detected
                        is_duplicate = False
                        for existing in all_faces:
                            if self._iou(loc, existing['location']) > 0.5:
                                is_duplicate = True
                                break

                        if not is_duplicate:
                            top, right, bottom, left = loc
                            face_img = rgb_image[top:bottom, left:right]
                            quality = self.assess_face_quality(face_img)

                            all_faces.append({
                                'location': loc,
                                'quality': quality,
                                'upsample_used': upsample
                            })

                # If we found good quality faces, no need to continue
                if any(f['quality'] > 0.6 for f in all_faces):
                    break

            except Exception as e:
                print(f"[DEBUG] Face detection at upsample={upsample} failed: {e}")
                continue

        # Sort by quality, return best
        all_faces.sort(key=lambda x: x['quality'], reverse=True)
        return all_faces

    def preprocess_face_for_angle(self, face_image: np.ndarray) -> np.ndarray:
        """
        Preprocess face to handle angle distortions.
        - Histogram equalization for lighting
        - Slight sharpening
        """
        if face_image is None or face_image.size == 0:
            return face_image

        # Convert to LAB color space
        lab = cv2.cvtColor(face_image, cv2.COLOR_BGR2LAB)

        # Apply CLAHE to L channel (adaptive histogram equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])

        # Convert back to BGR
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # Slight sharpening
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]]) / 9.0
        sharpened = cv2.filter2D(enhanced, -1, kernel)

        # Blend original and sharpened (50/50)
        result = cv2.addWeighted(enhanced, 0.7, sharpened, 0.3, 0)

        return result

    def recognize_with_angle_tolerance(
        self,
        face_encoding: np.ndarray,
        known_encodings: List[np.ndarray],
        known_names: List[str],
        face_quality: float = 1.0
    ) -> Tuple[str, float]:
        """
        Recognize face with adaptive tolerance based on quality.
        Lower quality (angled/distant) faces get higher tolerance.
        """
        if not known_encodings:
            return "Unknown", 0.0

        # Adjust tolerance based on face quality
        # Lower quality = higher tolerance
        adaptive_tolerance = self.base_tolerance
        if face_quality < 0.5:
            adaptive_tolerance = min(0.75, self.base_tolerance + 0.1)
        elif face_quality < 0.7:
            adaptive_tolerance = min(0.70, self.base_tolerance + 0.05)

        # Calculate distances
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)

        if len(face_distances) == 0:
            return "Unknown", 0.0

        # Find best match
        best_match_idx = face_distances.argmin()
        min_distance = face_distances[best_match_idx]

        # Check if within tolerance
        if min_distance < adaptive_tolerance:
            name = known_names[best_match_idx]
            # Convert distance to confidence (higher distance = lower confidence)
            confidence = 1.0 - min(min_distance / adaptive_tolerance, 1.0)

            # Penalize low quality matches slightly
            if face_quality < 0.6:
                confidence *= 0.9

            return name, confidence
        else:
            return "Unknown", 0.0

    def detect_and_recognize(
        self,
        person_region: np.ndarray,
        known_encodings: List[np.ndarray],
        known_names: List[str],
        model: str = "hog"
    ) -> Optional[Dict]:
        """
        Complete detection and recognition pipeline with robustness.

        Returns:
            Dict with face_bbox, name, confidence, quality or None
        """
        if person_region is None or person_region.size == 0:
            return None

        # Multi-scale face detection
        detected_faces = self.detect_faces_multiscale(person_region, model)

        if not detected_faces:
            return None

        # Use highest quality face
        best_face = detected_faces[0]
        location = best_face['location']
        quality = best_face['quality']

        # Check if quality is acceptable
        if quality < self.quality_threshold:
            print(f"[DEBUG] Face quality too low: {quality:.2f}")
            return None

        top, right, bottom, left = location

        # Extract and preprocess face
        rgb_region = cv2.cvtColor(person_region, cv2.COLOR_BGR2RGB)
        face_img = rgb_region[top:bottom, left:right]

        # Enhance face for angle/lighting issues
        enhanced_face_bgr = self.preprocess_face_for_angle(
            cv2.cvtColor(face_img, cv2.COLOR_RGB2BGR)
        )
        enhanced_face_rgb = cv2.cvtColor(enhanced_face_bgr, cv2.COLOR_BGR2RGB)

        # Get encoding from enhanced face
        try:
            encodings = face_recognition.face_encodings(
                enhanced_face_rgb,
                known_face_locations=[(0, enhanced_face_rgb.shape[1],
                                      enhanced_face_rgb.shape[0], 0)]
            )
        except:
            # Fallback to original if enhancement fails
            encodings = face_recognition.face_encodings(rgb_region, [location])

        if not encodings:
            return None

        encoding = encodings[0]

        # Recognize with adaptive tolerance
        name, confidence = self.recognize_with_angle_tolerance(
            encoding,
            known_encodings,
            known_names,
            quality
        )

        return {
            'face_bbox': [int(left), int(top), int(right), int(bottom)],
            'name': name,
            'confidence': confidence,
            'quality': quality
        }

    @staticmethod
    def _iou(box1: Tuple, box2: Tuple) -> float:
        """Calculate IoU between two face bounding boxes."""
        top1, right1, bottom1, left1 = box1
        top2, right2, bottom2, left2 = box2

        # Calculate intersection
        x_left = max(left1, left2)
        y_top = max(top1, top2)
        x_right = min(right1, right2)
        y_bottom = min(bottom1, bottom2)

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection = (x_right - x_left) * (y_bottom - y_top)

        # Calculate union
        box1_area = (right1 - left1) * (bottom1 - top1)
        box2_area = (right2 - left2) * (bottom2 - top2)
        union = box1_area + box2_area - intersection

        return intersection / union if union > 0 else 0.0


def enhance_frame_for_detection(frame: np.ndarray) -> np.ndarray:
    """
    Enhance entire frame for better person/face detection.
    - Auto white balance
    - Contrast enhancement
    """
    if frame is None or frame.size == 0:
        return frame

    # Auto white balance
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    avg_a = np.average(lab[:, :, 1])
    avg_b = np.average(lab[:, :, 2])
    lab[:, :, 1] = lab[:, :, 1] - ((avg_a - 128) * (lab[:, :, 0] / 255.0) * 0.5)
    lab[:, :, 2] = lab[:, :, 2] - ((avg_b - 128) * (lab[:, :, 0] / 255.0) * 0.5)
    balanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # Adaptive contrast
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    lab = cv2.cvtColor(balanced, cv2.COLOR_BGR2LAB)
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    return enhanced
