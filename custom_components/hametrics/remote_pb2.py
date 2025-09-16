"""Protobuf definitions for Prometheus Remote Write API."""

from typing import List


class Label:
    """Prometheus Label."""

    def __init__(self, name: str = "", value: str = ""):
        self.name = name
        self.value = value


class Sample:
    """Prometheus Sample."""

    def __init__(self, value: float = 0.0, timestamp: int = 0):
        self.value = value
        self.timestamp = timestamp


class TimeSeries:
    """Prometheus TimeSeries."""

    def __init__(self):
        self.labels: List[Label] = []
        self.samples: List[Sample] = []

    def add_label(self, name: str, value: str) -> Label:
        """Add a label and return it."""
        label = Label(name, value)
        self.labels.append(label)
        return label

    def add_sample(self, value: float, timestamp: int) -> Sample:
        """Add a sample and return it."""
        sample = Sample(value, timestamp)
        self.samples.append(sample)
        return sample


class WriteRequest:
    """Prometheus WriteRequest."""

    def __init__(self):
        self.timeseries: List[TimeSeries] = []

    def add_timeseries(self) -> TimeSeries:
        """Add a timeseries and return it."""
        ts = TimeSeries()
        self.timeseries.append(ts)
        return ts

    def SerializeToString(self) -> bytes:
        """Serialize to protobuf binary format."""
        try:
            return self._serialize_with_protobuf()
        except ImportError:
            # Fallback to simple binary encoding
            return self._serialize_simple()

    def _serialize_with_protobuf(self) -> bytes:
        """Serialize using proper protobuf library."""
        # This would require the actual compiled protobuf definitions
        # For now, use the simple serialization
        return self._serialize_simple()

    def _serialize_simple(self) -> bytes:
        """Simple protobuf-like serialization."""
        data = bytearray()

        for ts in self.timeseries:
            # Start timeseries message
            ts_data = bytearray()

            # Add labels
            for label in ts.labels:
                label_data = bytearray()

                # Field 1: name (string)
                name_bytes = label.name.encode("utf-8")
                label_data.extend(
                    self._encode_field(1, 2)
                )  # field 1, wire type 2 (length-delimited)
                label_data.extend(self._encode_varint(len(name_bytes)))
                label_data.extend(name_bytes)

                # Field 2: value (string)
                value_bytes = label.value.encode("utf-8")
                label_data.extend(self._encode_field(2, 2))
                label_data.extend(self._encode_varint(len(value_bytes)))
                label_data.extend(value_bytes)

                # Add label to timeseries (field 1)
                ts_data.extend(self._encode_field(1, 2))
                ts_data.extend(self._encode_varint(len(label_data)))
                ts_data.extend(label_data)

            # Add samples
            for sample in ts.samples:
                sample_data = bytearray()

                # Field 1: value (double)
                import struct

                value_bytes = struct.pack("<d", sample.value)
                sample_data.extend(
                    self._encode_field(1, 1)
                )  # field 1, wire type 1 (64-bit)
                sample_data.extend(value_bytes)

                # Field 2: timestamp (int64)
                sample_data.extend(
                    self._encode_field(2, 0)
                )  # field 2, wire type 0 (varint)
                sample_data.extend(self._encode_varint(sample.timestamp))

                # Add sample to timeseries (field 2)
                ts_data.extend(self._encode_field(2, 2))
                ts_data.extend(self._encode_varint(len(sample_data)))
                ts_data.extend(sample_data)

            # Add timeseries to write request (field 1)
            data.extend(self._encode_field(1, 2))
            data.extend(self._encode_varint(len(ts_data)))
            data.extend(ts_data)

        return bytes(data)

    def _encode_field(self, field_num: int, wire_type: int) -> bytes:
        """Encode field number and wire type."""
        return self._encode_varint((field_num << 3) | wire_type)

    def _encode_varint(self, value: int) -> bytes:
        """Encode a varint."""
        if value < 0:
            # Handle negative numbers (not needed for this use case)
            value = (1 << 64) + value

        result = bytearray()
        while value >= 0x80:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value & 0x7F)
        return bytes(result)
