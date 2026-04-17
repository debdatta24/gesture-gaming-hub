import cv2
import mediapipe as mp


class HandTracker:

    def __init__(self):

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6
        )

        self.mp_draw = mp.solutions.drawing_utils


    def detect_hands(self, frame):

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = self.hands.process(rgb)

        landmarks = None

        if results.multi_hand_landmarks:

            for hand_landmarks in results.multi_hand_landmarks:

                self.mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS
                )

                landmarks = hand_landmarks.landmark

        return frame, landmarks


    def get_fist_state(self, landmarks):

        if landmarks is None:
            return "none"

        tips = [8, 12, 16, 20]
        folded = 0

        for tip in tips:

            if landmarks[tip].y > landmarks[tip-2].y:
                folded += 1

        if folded >= 3:
            return "fist"

        else:
            return "open"