% generate_sweep.m
fs = 44100;            % Sample rate
duration = 5;          % Duration of sweep in seconds
f_start = 100;         % Start frequency Hz
f_end = 10000;         % End frequency Hz
amplitude = 0.8;       % Amplitude (max 1)

t = 0:1/fs:duration;
sweep = chirp(t, f_start, duration, f_end);

% Normalize and scale
sweep = amplitude * sweep / max(abs(sweep));

audiowrite('sweep_test.wav', sweep, fs);

fprintf('Sweep test tone generated: sweep_test.wav\n');
