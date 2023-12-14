from src.main import get_puzzles, ToTSolver

if __name__ == '__main__':
    puzzles = get_puzzles()
    # cot_solve(puzzles)
    puzzle = '4 5 6 10\n10 - 4 = 6 (left: 5 6 6)\n5 * 6 = 30 (left: 30 6)\n30 - 6 = 24 (left: 24)'
    totsolver = ToTSolver(puzzle, 1)
    totsolver.solve()
