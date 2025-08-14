% analyze_recording.m
[rec_signal, fs] = audioread('mic_recording.wav');

% Remove DC offset
rec_signal = rec_signal - mean(rec_signal);

% FFT
N = length(rec_signal);
f_axis = linspace(0, fs/2, floor(N/2));

REC_FFT = abs(fft(rec_signal));
REC_FFT = REC_FFT(1:floor(N/2));

% Normalize FFT magnitude
REC_FFT_dB = 20*log10(REC_FFT / max(REC_FFT));

figure;
plot(f_axis, REC_FFT_dB);
title('Frequency Response of Recorded Signal');
xlabel('Frequency (Hz)');
ylabel('Magnitude (dB)');
grid on;

% Estimate SNR (crude)
signal_power = rms(rec_signal)^2;
noise_floor = median(REC_FFT_dB); % approx noise floor level in dB
snr_estimate = max(REC_FFT_dB) - noise_floor;
fprintf('Approximate SNR (dB): %.2f\n', snr_estimate);
