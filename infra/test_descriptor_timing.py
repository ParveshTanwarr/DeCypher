from infra.detectors.descriptor_timing import (
    detect_descriptor_timing
)


result = detect_descriptor_timing(
    "http://127.0.0.1:8000/"
)


print("Descriptor timing result:")
print(result)