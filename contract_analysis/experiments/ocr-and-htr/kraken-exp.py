# Import required libraries
from kraken import blla
from kraken.lib import models
from kraken import rpred

recognition_model_path = "models/german/german_print.mlmodel"


def segment_baseline(im):
    """
    Segment the image into lines using CoreML model.
    """
    return blla.segment(
        im,
        text_direction="horizontal-lr",
    )


def run_recognition(im):
    """
    Run recognition on the image using kraken.
    """
    rec_model = models.load_any(recognition_model_path)

    pred_it = rpred.rpred(
        network=rec_model,
        im=im,
        bounds=segment_baseline(im),
        pad=16,
        bidi_reordering=True,
    )

    for record in pred_it:
        confidence = (
            sum(record.confidences) / len(record.confidences)
            if record.confidences
            else 0
        )
        print(f"Text: {record.prediction} (Confidence: {confidence:.2f})")
