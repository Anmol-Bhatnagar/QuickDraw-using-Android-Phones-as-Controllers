import cv2

def main():
    # Open the default webcam (device 0)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    print("Webcam opened successfully. Press ESC to exit.")
    
    while True:
        # Read a frame from the webcam
        ret, frame = cap.read()
        
        if not ret:
            print("Error: Failed to grab frame.")
            break
            
        # Draw text in the top-left corner
        # cv2.putText(img, text, org(x, y), font, fontScale, color(B, G, R), thickness, lineType)
        cv2.putText(
            frame, 
            "STATE: TESTING", 
            (20, 50), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            1.0, 
            (0, 255, 0), # Green text
            2, 
            cv2.LINE_AA
        )
        
        # Display the frame in a window named "Quickdraw"
        cv2.imshow('Quickdraw', frame)
        
        # Wait 1ms for a key event, exit if ESC (ASCII 27) is pressed
        if cv2.waitKey(1) == 27:
            print("ESC pressed. Exiting...")
            break

    # Clean up: release the capture object and close the window
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
