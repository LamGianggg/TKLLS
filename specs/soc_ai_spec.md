# Hardware Specification: Autonomous AI Accelerator SoC (Spec2RTL Golden Reference)

## 1. System Overview
This specification defines an autonomous Single-Chip System-on-Chip (SoC) designed to perform hardware-accelerated vector dot products and neural network inference. The SoC integrates:
1. **CPU Micro-sequencer (`cpu_controller`)**: Coordinates system initialization, RAM preloading, DMA initiation, interrupt handling, and result latching.
2. **On-Chip SRAM (`ram_16x4`)**: Stores 4-bit weights and inputs in a 16-word by 4-bit addressable memory space.
3. **Direct Memory Access Controller (`dma_8237`)**: High-throughput 8237-compatible bus master transferring operands directly from RAM to the AI Core without CPU overhead.
4. **AI Accelerator Core (`ai_core`)**: Pipelined vector execution engine containing a Multiply-Accumulate (MAC) Unit, ReLU non-linear activation, and autonomous FSM control.
5. **Bus Arbitration System**: Multi-channel 2-to-1 multiplexers dynamically switching RAM address and control lines between CPU and DMA master modes.

---

## 2. Chip-Level Interface Ports

| Port Name | Direction | Width | Description |
| :--- | :---: | :---: | :--- |
| `clk` | Input | 1 | Global system clock. |
| `clr` | Input | 1 | Active-high asynchronous system reset. |
| `SYS_COMPLETE` | Output | 1 | Asserted high when the entire system workflow finishes and result is stable. |
| `FINAL_RESULT` | Output | 8 | 8-bit final processed dot product output latched by CPU. |
| `CPU_STATE` | Output | 4 | Current CPU microcode state ($S00 \to S10$). |
| `AI_DONE` | Output | 1 | Asserted high when AI calculation completes. |
| `SYSTEM_INTR` | Output | 1 | Hardware interrupt line from AI Core to CPU. |
| `TC` | Output | 1 | Terminal count indicator from DMA controller. |
| `DACK` | Output | 1 | DMA acknowledge signal. |
| `DREQ` | Output | 1 | DMA request signal from AI Core. |

---

## 3. Subsystem Specifications

### 3.1. CPU Micro-Sequencer (`cpu_controller`)
- **FSM States**:
  - `S00` (4'h0): Idle / Reset state.
  - `S01` (4'h1): RAM write setup for Weight $W$ (Address `2'b00`, Data `4'b0011` = 3).
  - `S02` (4'h2): RAM write pulse assert for Weight $W$.
  - `S03` (4'h3): RAM write setup for Input $X$ (Address `2'b01`, Data `4'b0100` = 4).
  - `S04` (4'h4): RAM write pulse assert for Input $X$.
  - `S05` (4'h5): DMA configuration: Write MAR low byte with start address `16'h0000`.
  - `S06` (4'h6): DMA configuration: Write WCR with transfer count `16'h0001` (2 words: W and X).
  - `S07` (4'h7): Start pulse generation (`START_AI = 1`, `AI_IE = 1`).
  - `S08` (4'h8): Bus grant to DMA (`DMA_MODE_SEL = 1`, `DMA_HLDA = 1`); wait for `SYSTEM_INTR`.
  - `S09` (4'h9): Interrupt acknowledged; switch bus back to CPU (`DMA_MODE_SEL = 0`).
  - `S10` (4'hA): Latch AI result into `FINAL_RESULT`, assert `SYS_COMPLETE = 1`.

### 3.2. RAM 16x4 (`ram_16x4`)
- Synchronous write, asynchronous/transparent read.
- Address width: 2 bits (rows 0..3 accessed). Data width: 4 bits.
- Controls: `CS` (Chip Select, active high), `RWS` (Read/Write Select: 1 = Write, 0 = Read).

### 3.3. DMA Controller (`dma_8237`)
- Address Register (MAR): 16-bit auto-incrementing memory address register.
- Word Count Register (WCR): 16-bit auto-decrementing transfer counter.
- Generates `DACK` in response to `DREQ`.
- Outputs `TC = 1` when `WCR == 0`.
- Issues RAM read control `DMA_RAM_CS = 1`, `DMA_RAM_RWS = 0`.

### 3.4. AI Accelerator Core (`ai_core`)
- **Datapath (`ai_datapath`)**:
  - `Reg_W` (4-bit): Latches weight operand on first DMA transfer cycle.
  - `Reg_X` (4-bit): Latches input operand on second DMA transfer cycle.
  - `MAC_Unit` (8-bit): Computes $P = W \times X$ (4x4 multiplier), accumulated into 8-bit accumulator register: $\text{Acc} \Leftarrow \text{Acc} + P$.
  - `ReLU_Unit`: Non-linear function $R = (Acc > 0) ? Acc : 0$.
  - `Reg_Result` (8-bit): Output register holding the activated result.
- **Controller (`ai_fsm`)**:
  - Cycles through states `T0` to `T6` to orchestrate `DREQ`, operand latching, MAC trigger, ReLU enable, and asserting `AI_DONE` & `SYSTEM_INTR`.

---

## 4. Verification Benchmark & Golden Criteria
- **Input Data**:
  - Weight: $W = 3$ (`4'b0011` at address `0x00`).
  - Input: $X = 4$ (`4'b0100` at address `0x01`).
- **Expected Operation**:
  - Product: $P = 3 \times 4 = 12 = \text{0x0C}$.
  - Post-ReLU Result: $12 = \text{0x0C}$ (`8'b00001100`).
- **Target Timing Verification**:
  - At cycle completion ($t \approx 595\,\text{ns}$):
    - `SYS_COMPLETE == 1'b1`
    - `CPU_STATE == 4'hA` (`S10`)
    - `FINAL_RESULT == 8'h0C` (Decimal 12)
