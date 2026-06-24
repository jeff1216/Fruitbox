import numpy as np


WEIGHTS = [0.60, 0.3, 0.1, 0, 0, 0, 0, 0, 0]  # weights for 2-10


class FruitBoxGrid:
    def __init__(self, rows=10, columns=17, rng=None):
        self.rows = rows
        self.columns = columns
        self.grid = None
        self.empty_count = rows * columns
        self.rng = rng or np.random.default_rng()

    def weighted_random(self):
        return self.rng.choice(np.arange(2, 11), p=WEIGHTS)

    def generate(self, type):
        if type == "random":
            self.grid = self.rng.integers(1, 10, size=(self.rows, self.columns))
            return self.grid

        if type == "solvable":
            self.grid = np.full((self.rows, self.columns), -1)
            self.empty_count = self.rows * self.columns
            while not self.isGridDone():
                if self.empty_count == 1:
                    break
                tuple_size = self.weighted_random()
                while tuple_size > self.empty_count or self.empty_count - tuple_size == 1:
                    tuple_size = self.weighted_random()

                rect = self.random_rect(tuple_size)
                if rect is None:
                    continue

                r1, c1, r2, c2 = rect
                numbers = self._numbers_summing_to_10(tuple_size)
                idx = 0
                newly_placed = set()
                for i in range(r1, r2 + 1):
                    for j in range(c1, c2 + 1):
                        if self.grid[i][j] == -1:
                            self.grid[i][j] = numbers[idx]
                            newly_placed.add((i, j))
                            idx += 1
                self.empty_count -= tuple_size
                # print(f"placed {tuple_size} cells at ({r1},{c1})->({r2},{c2}), empty_count={self.empty_count}")
                # self._print_grid(newly_placed)

            return self.grid


    def _numbers_summing_to_10(self, count):
        while True:
            cuts = sorted(self.rng.integers(1, 10, size=count - 1).tolist())
            if len(set(cuts)) < len(cuts):
                continue
            parts = [cuts[0]] + [cuts[i] - cuts[i-1] for i in range(1, len(cuts))] + [10 - cuts[-1]]
            ALLOWED_WITH_ONE = {(1,2,2,5), (1,2,3,4), (1,3,3,3)}
            s = tuple(sorted(parts))
            if count == 4 and 1 in parts and s not in ALLOWED_WITH_ONE:
                continue
            if all(1 <= p <= 9 for p in parts) and sorted(parts) != [1, 1, 8]:
                return parts

    def random_rect(self, tuple_size, max_attempts=1000):
        if tuple_size > self.empty_count:
            return None

        if self.rng.random() < 0.3:
            for _ in range(max_attempts):
                ra, rb = int(self.rng.integers(0, self.rows)),   int(self.rng.integers(0, self.rows))
                ca, cb = int(self.rng.integers(0, self.columns)), int(self.rng.integers(0, self.columns))
                r1, r2 = min(ra, rb), max(ra, rb)
                c1, c2 = min(ca, cb), max(ca, cb)
                if self.checkEmptySlots(r1, c1, r2, c2, tuple_size):
                    # print("rand rect")
                    return r1, c1, r2, c2
            return None
        else:
            best, best_area = None, 0
            ban_2x2 = tuple_size in (2, 4)
            for _ in range(max_attempts):
                ra, rb = int(self.rng.integers(0, self.rows)),   int(self.rng.integers(0, self.rows))
                ca, cb = int(self.rng.integers(0, self.columns)), int(self.rng.integers(0, self.columns))
                r1, r2 = min(ra, rb), max(ra, rb)
                c1, c2 = min(ca, cb), max(ca, cb)
                if ban_2x2 and (r2 - r1 + 1) == 2 and (c2 - c1 + 1) == 2:
                    continue
                area = (r2 - r1 + 1) * (c2 - c1 + 1)
                if area <= best_area or not self.checkEmptySlots(r1, c1, r2, c2, tuple_size):
                    continue
                sub = self.grid[r1:r2+1, c1:c2+1] == -1
                if (sub[:, :-1] & sub[:, 1:]).any() or (sub[:-1, :] & sub[1:, :]).any():
                    continue
                best, best_area = (r1, c1, r2, c2), area
            # print("best rect")
            return best

    def _print_grid(self, newly_placed=None):
        NEW  = '\033[1;92m'
        DIM  = '\033[2m'
        RST  = '\033[0m'
        lines = []
        for i in range(self.rows):
            row = []
            for j in range(self.columns):
                v = self.grid[i][j]
                if v == -1:
                    row.append(f'{DIM} ·{RST}')
                elif newly_placed and (i, j) in newly_placed:
                    row.append(f'{NEW}{v:2}{RST}')
                else:
                    row.append(f'{v:2}')
            lines.append(' '.join(row))
        print('\n'.join(lines))

    def checkEmptySlots(self, r1, c1, r2, c2, empty):
        count_empty = 0
        for i in range(r1, r2 + 1):
            for j in range(c1, c2 + 1):
                if self.grid[i][j] == -1:
                    count_empty += 1
        return count_empty == empty
    
    def isGridDone(self):
        for i in range(self.rows):
            for j in range(self.columns):
                if self.grid[i][j] == -1:
                    return False
        return True
