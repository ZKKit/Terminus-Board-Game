# TERMINUS

Terminus is an original, deterministic, perfect-information abstract strategy game played on a 12×12 grid. It features a minimal rule set that generates an enormous, non-solvable decision tree. Every capture permanently alters the board’s topology, forcing players to balance mobility, territorial control, and irreversible commitments.

There is no dice, hidden information, or point-tracking. Victory emerges purely from graph manipulation and strategic foresight.

## Game Instructions & Setup
* **Requirements:** Python 3.8+ and Pygame 2.5+.

* **Controls:** Left-click a piece to select it. Left-click a highlighted square to move or capture. Use the right sidebar to resign, flip the board, or copy the move log.

## Game Rules
**Objective:** You win by achieving **one** of the following outcomes (evaluated in strict priority order):
1.  **Mobile Extinction:** Reduce your opponent to zero Pawns (Mobile).
2.  **Mobility Starvation:** Leave your opponent with zero legal moves at the start of their turn.
3.  **Complete Isolation:** Secure more empty territory than your opponent when the board fully partitions into single-color zones.

**Turn Mechanics:**
Black moves first. On your turn, you must perform exactly one action:
* **Shift:** Move a Mobile Pawn exactly 1 square in any of the 8 directions to an empty square.
* **Capture & Boundary Formation:** Move a Mobile Pawn onto an enemy-occupied square to remove that piece. 
    * *Constraint:* To capture, your piece must start its turn **orthogonally adjacent** to a friendly piece (Pawn, Trapped Pawn, or Boundary Marker).
    * *State Change:* The capturing piece instantly and permanently becomes a **Boundary Marker**. It can never move or capture again, but it provides orthogonal support and blocks movement.

**The Isolation Rule:**
Boundary Markers and board edges divide the grid into independent partitions. If a partition is ever completely sealed and contains **zero enemy Mobile Pawns**, the Isolation Trigger activates. All Mobile Pawns inside that partition permanently become **Trapped Pawns**. They can never move again. 

## Strategy & Ideas Implemented
Terminus is a "Cold War" game. Engaging the enemy (capturing) removes their material but permanently freezes your attacking piece into terrain. 
* **Support Networks:** Because captures require orthogonal support, players must move in phalanxes. Lone pawns are heavily penalized.
* **Topological Density:** Players must balance the desire to build unbreakable walls (which trap enemy pieces via Isolation) against the risk of creating too much "scar tissue" that chokes their own mobility.
* **Skills Tested:** Forward prediction, spatial logic constraint optimization, strategy designing, tactical skills, and Nash Equilibrium seeking in the Game Theory.

## License
This project is licensed under the **PolyForm Noncommercial License 1.0.0**. 
Personal and educational use is encouraged. Commercial use is strictly prohibited
without prior written permission from the author.
Author: ZKKit (Github: https://github.com/ZKKit)
