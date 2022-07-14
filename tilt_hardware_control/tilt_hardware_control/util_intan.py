
from typing import List, Optional
import time
import socket
from pprint import pprint

COMMAND_BUFFER_SIZE = 1024

class Intan:
    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect(('127.0.0.1', 5000))
        self._socket.settimeout(1)
        
        runmode = self.cmd('get runmode')
        self._running = runmode == 'Run'
    
    def start_recording(self):
        if not self._running:
            runmode = self.cmd([
                'set runmode run',
                # 'get runmode',
            ], add_get=False)
            time.sleep(0.05)
            runmode = self.cmd('get runmode')
            self._running = runmode == 'Run'
            assert self._running
    
    def stop_recording(self):
        if self._running:
            runmode = self.cmd([
                'set runmode stop',
            ], add_get=False)
            time.sleep(0.05)
            runmode = self.cmd('get runmode')
            self._running = runmode == 'Run'
            assert not self._running
    
    def cmd(self, cmd, *, add_get = True):
        if not isinstance(cmd, list):
            cmds = [cmd]
            non_list = True
        else:
            cmds = cmd
            non_list = False
        
        return_count = 0
        for c in cmds:
            if c.startswith('get '):
                return_count += 1
        
        if return_count == 0 and add_get:
            cmds.append('get Version')
            return_count = 1
            added_return = True
            # added_return = False
        else:
            added_return = False
        
        cmd_str = ";".join(cmds)
        
        self._socket.sendall(cmd_str.encode())
        response = []
        
        # example exchange
        # get type
        # Return: Type ControllerStimRecordUSB2
        
        if return_count:
            for _ in range(return_count):
                return_str = str(self._socket.recv(COMMAND_BUFFER_SIZE), "utf-8")
                # print(cmd_str)
                # print(return_str)
                # if return_str.startswith('Error '):
                if not return_str.startswith('Return:'):
                    raise ValueError(return_str)
                _, return_str = return_str.split(':') # remove "Return:"
                _, return_val = return_str.strip().split(' ') # remove variable name
                if return_val == 'True':
                    response.append(True)
                elif return_val == 'False':
                    response.append(False)
                else:
                    try:
                        response.append(int(return_val))
                    except ValueError:
                        try:
                            response.append(float(return_val))
                        except ValueError:
                            response.append(return_val)
        
        if not response or added_return:
            return None
        elif non_list:
            assert len(response) == 1
            return response[0]
        else:
            return response
    
    def wait_for_upload(self):
        in_prog = True
        while in_prog:
            in_prog = self.cmd('get UploadInProgress')
            # print('in prog', in_prog, repr(in_prog))
    
    def close(self):
        self._socket.close()

class Stimulator:
    def __init__(self, channels: List[str]):
        self.intan = Intan()
        # self.channel = 'a-000'
        self.channels = channels
        self.digital_out = 'digital-out-01'
        
        # the current channel with stimenabled true
        self._selected_channel: Optional[str] = None
        
        # send commands for each channel separately so the channel that
        # caused an error can be known
        for ch in self.channels:
            self.intan.cmd([
                f'set {ch}.StimEnabled false',
                f'set {ch}.TriggerEdgeOrLevel edge',
                f'set {ch}.TriggerHighOrLow high',
                f'set {ch}.source keypressf1',
            ])
        
        self.intan.cmd([
            f'set {self.digital_out}.source keypressf1',
            f'set {self.digital_out}.StimEnabled true',
            f'set {self.digital_out}.TriggerEdgeOrLevel edge',
            f'set {self.digital_out}.TriggerHighOrLow high',
            f'set {self.digital_out}.PulseOrTrain SinglePulse',
            f'set {self.digital_out}.PostTriggerDelayMicroseconds 0',
            # 2 ms pulse to make sure it's recordable with analog inputs
            f'set {self.digital_out}.FirstPhaseDurationMicroseconds 2000',
            f'set {self.digital_out}.RefractoryPeriodMicroseconds 0',
        ])
    
    def set_stimulation_parameters(self, *,
        channel: Optional[str] = None,
        first_phase_amplitude: float,
        first_phase_duration: float,
        second_phase_amplitude: float,
        second_phase_duration: float,
        number_of_pulses: int = 1,
        pulse_train_period: float = None,
    ):
        if channel is None:
            assert len(self.channels) == 1
            channel = self.channels[0]
        assert channel in self.channels
        
        self.intan.stop_recording()
        
        ch = channel
        cmds = [
            f'set {ch}.StimEnabled true',
            f'set {ch}.firstphaseamplitudemicroamps {first_phase_amplitude}',
            f'set {ch}.firstphasedurationmicroseconds {first_phase_duration}',
            f'set {ch}.secondphaseamplitudemicroamps {second_phase_amplitude}',
            f'set {ch}.secondphasedurationmicroseconds {second_phase_duration}',
        ]
        if self._selected_channel is not None:
            cmds.append(f'set {self._selected_channel}.StimEnabled false')
        assert number_of_pulses >= 1
        if number_of_pulses == 1:
            cmds.append(f'set {ch}.PulseOrTrain SinglePulse')
        else:
            assert pulse_train_period is not None
            cmds.extend([
                f'set {ch}.PulseOrTrain PulseTrain',
                f'set {ch}.NumberOfStimPulses {number_of_pulses}',
                f'set {ch}.PulseTrainPeriodMicroseconds {pulse_train_period}',
            ])
        
        self.intan.cmd(cmds)
        self._selected_channel = channel
        self.intan.wait_for_upload()
        self.intan.start_recording()
    
    def trigger_stimulus(self):
        self.intan.cmd('execute manualstimtriggerpulse f1')
    
    def close(self):
        try:
            self.intan.stop_recording()
        finally:
            self.intan.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *exc):
        self.close()
