#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <ltc.h>
#include <vector>

namespace py = pybind11;

class LTCWrapper {
public:
    LTCWrapper(int sample_rate, int fps) : sample_rate(sample_rate) {
        // Initialize LTC decoder
        decoder = ltc_decoder_create(sample_rate, fps * 80);
    }

    ~LTCWrapper() {
        if (decoder) {
            ltc_decoder_free(decoder);
        }
    }

    py::tuple decode_audio(py::array_t<float> audio) {
        auto buf = audio.request();
        float* ptr = (float*)buf.ptr;
        size_t len = buf.size;

        // Convert float samples to unsigned char
        std::vector<unsigned char> samples(len);
        for (size_t i = 0; i < len; i++) {
            // Scale and offset to convert -1.0 to 1.0 range to 0-255
            samples[i] = (unsigned char)((ptr[i] + 1.0f) * 127.5f);
        }

        // Write audio to decoder
        ltc_decoder_write(decoder, samples.data(), len, 0);

        // Read frames
        LTCFrameExt frame;
        while (ltc_decoder_read(decoder, &frame)) {
            // Convert frame to Python tuple
            return py::make_tuple(
                frame.ltc.frame_units + frame.ltc.frame_tens * 10,
                frame.ltc.secs_units + frame.ltc.secs_tens * 10,
                frame.ltc.mins_units + frame.ltc.mins_tens * 10,
                frame.ltc.hours_units + frame.ltc.hours_tens * 10,
                frame.off_start / (double)sample_rate
            );
        }

        return py::make_tuple();
    }

private:
    LTCDecoder* decoder;
    int sample_rate;
};

PYBIND11_MODULE(ltc_wrapper, m) {
    py::class_<LTCWrapper>(m, "LTCWrapper")
        .def(py::init<int, int>())
        .def("decode_audio", &LTCWrapper::decode_audio);
} 