import asyncio
from itertools import combinations, permutations
from typing import Dict, List, Set, Tuple

alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def char_to_index(c: str) -> int:
    """
    字符转为索引
    """
    return ord(c) - ord("A")


def index_to_char(i: int) -> str:
    """
    索引转为字符
    """
    return chr(i + ord("A"))


class Enigma:
    """
    模拟 Enigma 机
    """
    @staticmethod
    def __read_conf_row(row: str) -> Dict[str, str]:
        result = {}
        for pair_str in row.split(", "):
            pair = pair_str.split("-")
            result[pair[0]] = pair[1]
        return result

    @staticmethod
    def __apply_ring_setting(letter: str, ring_setting: int) -> str:
        return chr((char_to_index(letter) + ring_setting) % 26 + ord("A"))

    def __init__(self) -> None:
        conf_rows: List[str]
        with open("config.txt", "r") as f:
            conf_rows = f.read().splitlines()

        self.reflector = Enigma.__read_conf_row(conf_rows[1])

        # 这里按照配置文件中顺序读取转子接线保存
        self.__rotors: List[str] = []  # List[original_foward_sequence]
        for i in [3, 5, 7]:
            self.__rotors.append(
                "".join(Enigma.__read_conf_row(conf_rows[i]).values()))
        # 这是加密中真正使用的模拟转子，通过 init_rotors 函数生成
        # List[(forward_sequence, backward_sequence)]
        self.rotors: List[Tuple[str, str]] = []
        self.r_pos = [0, 0, 0]
        self.__rotors_turn_pos = [char_to_index(l) + 1 for l in [
            "Q", "E", "V"]]  # pos == turn_pos 时下一个转

        # 插线板，用 init_plugboard 函数设置
        self.plugboard = {}

        self.ring_settings = [char_to_index(i)
                              for i in conf_rows[9].split("-")]
        self.ring_settings.reverse()  # rotor_order 是倒序

    def set_init_pos(self, pos: List[int]):
        """
        设置初始位置（从低到高，反过来）
        """
        self.r_pos = pos[:]
        self.r_pos.reverse()
        self.__init_pos = self.r_pos[:]

    def reset_pos(self):
        """
        重置为最近设置的初始位置
        """
        self.r_pos = self.__init_pos.copy()

    def turn_rotor(self, times: int):
        """
        旋转一次转子（在加密前调用，像真正的 Enigma 一样）
        """
        for _ in range(times):
            i = 0
            while i < 3:
                self.r_pos[i] += 1
                if self.r_pos[i] == 26:
                    self.r_pos[i] = 0
                if self.r_pos[i] == self.rotors_turn_pos[i]:
                    i += 1
                else:
                    break

    def init_rotors(self, rotor_order: List[int]):
        """
        初始化转子：应用转子顺序、ring settings，生成反向序列（反向通过转子时的字母序列）
        """
        order = rotor_order.copy()
        order.reverse()
        self.rotors = []
        self.rotors_turn_pos = []
        for i, s in enumerate(self.ring_settings):
            o_rotor = self.__rotors[order[i]]
            self.rotors_turn_pos.append(self.__rotors_turn_pos[order[i]])

            # 应用 ring settings
            # ref: https://crypto.stackexchange.com/a/71327
            dot_pos = (list(o_rotor).index("A") + s) % 26
            rotor = "".join(Enigma.__apply_ring_setting(c, s)
                            for c in list(o_rotor))
            while rotor[dot_pos] != index_to_char(s):
                rotor = rotor[-1:] + rotor[:-1]

            # 生成反向 rotor
            rotor_backward = "".join(
                [index_to_char(rotor.index(c)) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"])

            self.rotors.append((rotor, rotor_backward))

    def __apply_rotors(self, letter: str, backward: int = 0) -> str:
        rotors = self.rotors.copy()
        poses = self.r_pos.copy()
        if backward:
            rotors.reverse()
            poses.reverse()
        for i, r in enumerate(rotors):
            seq = r[backward]
            pos = poses[i]
            letter = seq[(char_to_index(letter) + pos) % 26]
            letter = index_to_char((char_to_index(letter) - pos + 26) % 26)
        return letter

    def set_plugboard(self, pairs: Set[Tuple[str, str]]):
        """
        设置插线板
        插线板是要交换的字母对的集合
        """
        self.plugboard = {}
        for k, v in pairs:
            if k != v:
                self.plugboard[k] = v
                self.plugboard[v] = k

    def process(self, letter: str, plugboard: bool = False) -> str:
        """
        加密一个字母
        """
        r = letter
        if plugboard and r in self.plugboard:
            r = self.plugboard[r]
        r = self.__apply_rotors(r)
        r = self.reflector[r]
        r = self.__apply_rotors(r, backward=1)
        if plugboard and r in self.plugboard:
            r = self.plugboard[r]
        return r

    def copy(self):
        """
        复制 Enigma，要求已经调用过 init_rotors, set_init_pos
        """
        enigma = Enigma()
        enigma.r_pos = self.r_pos.copy()
        enigma.__init_pos = self.__init_pos.copy()
        enigma.rotors = self.rotors.copy()
        enigma.plugboard = self.plugboard.copy()
        enigma.rotors_turn_pos = self.rotors_turn_pos.copy()
        return enigma


def find_ring(message: str, cryptotext: str,  current: str,
              ring: List[int], ring_idx: List[str]):
    """
    递归查找环
    返回结构：P_{ring_idx[i]}(ring[i]) = ring[(i + 1) % len(ring)]
    特别的，ring_idx[i] < 0 表示 P^{-1}_{ring_idx[i]}
    """
    for i in range(len(message)):
        if message[i] == current:
            ring.append(message[i])
            ring_idx.append(i)
            try:
                index = ring.index(cryptotext[i])
            except:
                ret = find_ring(message, cryptotext,
                                cryptotext[i], ring, ring_idx)
                if not ret:
                    ring.pop()
                    ring_idx.pop()
                else:
                    return ret
            else:
                return ring[index:], ring_idx[index:]

    for i in range(len(message)):
        if cryptotext[i] == current:
            ring.append(cryptotext[i])
            ring_idx.append(-i)
            try:
                index = ring.index(message[i])
            except:
                ret = find_ring(message, cryptotext,
                                message[i], ring, ring_idx)
                if not ret:
                    ring.pop()
                    ring_idx.pop()
                else:
                    return ret
            else:
                return ring[index:], ring_idx[index:]

    return None


def find_rings(message: str, cryptotext: str) -> List[List[Tuple[str, int]]]:
    """
    根据消息和密文，找出所有的环
    """
    ret_rings = []
    for i in range(0, len(message)):
        ret = find_ring(message, cryptotext, cryptotext[i], [message[i]], [i])
        if ret and ret not in ret_rings:
            ret_rings.append(ret)
    for i in range(0, len(message)):
        ret = find_ring(message, cryptotext, message[i], [cryptotext[i]], [-i])
        if ret and ret not in ret_rings:
            ret_rings.append(ret)
    # 可能有顺序不同的重复环，去掉
    rings_no_dup = []
    sorted_rings = []
    for r in ret_rings:
        s = sorted(r[0])
        if s not in sorted_rings:
            sorted_rings.append(s)
            rings_no_dup.append(r)

    # 会返回形如 [x, -x] 的，去掉
    to_remove_idx = []
    for i in range(0, len(rings_no_dup)):
        ring_idx = rings_no_dup[i][1]
        if ring_idx[0] == -ring_idx[1]:
            to_remove_idx.append(i)
    for i in reversed(to_remove_idx):
        rings_no_dup.pop(i)

    # 从两个 array 转换为一个 array[tuple]
    rings = []
    for ring, ring_idx in rings_no_dup:
        r = []
        for i in range(0, len(ring_idx)):
            r.append((ring[i], ring_idx[i]))
        rings.append(r)
    return rings


def check_pair_conflict(pair0: Tuple[str, str], pair1: Tuple[str, str]) -> bool:
    """
    检查两个插线板交换对是否冲突
    具体地，它们是否将同一字母交换为两个不同字母
    """
    return (pair0[0] == pair1[1] and pair0[1] != pair1[0]) or\
        (pair0[1] == pair1[1] and pair0[0] != pair1[0]) or\
        (pair0[0] == pair1[0] and pair0[1] != pair1[1]) or\
        (pair0[1] == pair1[0] and pair0[0] != pair1[1])


async def try_order_pos(rotor_order: List[int], init_pos: List[int],
                        rings: List[List[Tuple[str, int]]]) \
        -> Tuple[List[int], List[int], List[Set[Tuple[str, str]]]]:
    """
    阶段 1：猜测转子排序和初始位置
    """
    found = True
    plugboards: List[Set[Tuple[str, str]]] = []  # 记录可能的插线板设置
    enigma = Enigma()
    enigma.init_rotors(rotor_order)
    enigma.set_init_pos(init_pos)
    for ring in rings:
        ring_found = False
        p_pairs: List[Tuple[str, str]] = []
        for try_letter in alphabet:
            letter = try_letter
            for _, index in ring:
                enigma.set_init_pos(init_pos)
                enigma.turn_rotor(abs(index) + 1)  # P_{-k} 与 P_{k} 等价
                letter = enigma.process(letter)
            if letter == try_letter:
                orig_letter = ring[0][0]
                l_index = char_to_index(letter)
                o_index = char_to_index(orig_letter)
                front = min(l_index, o_index)
                back = max(l_index, o_index)
                p_pairs.append(
                    (index_to_char(front), index_to_char(back)))
                ring_found = True
        if not ring_found:
            found = False
            break
        if not len(plugboards):
            for pair in p_pairs:
                plugboards.append(set([pair]))
        else:
            new_plugboards = []
            for pb in plugboards:
                for pair in p_pairs:
                    # 每一个现有配置和每一个新找到的对产生一组新配置
                    conflict = False
                    for exists_p in pb:
                        if check_pair_conflict(pair, exists_p):
                            # 与现有交换对冲突
                            conflict = True
                            break
                    if not conflict:
                        new_pb = pb.copy()
                        new_pb.add(pair)
                        new_plugboards.append(new_pb)
            if not len(new_plugboards):
                # 没有可行的插线板配置
                found = False
                break
            plugboards = new_plugboards
    if not found:
        return None
    return rotor_order, init_pos, plugboards


def extend_plugboard(msg: str, cryptotext: str,
                     enigma: Enigma, plugboard: Set[Tuple[str, str]]):
    """
    用明密文拓展已知插线板配置，并找到不应出现于插线板剩余部分的字母
    """
    iter_found = True
    except_chars = set()
    for k, v in plugboard:
        except_chars.add(k)
        except_chars.add(v)
    used_pos = set()
    while iter_found:
        enigma.set_plugboard(plugboard)
        iter_found = False
        for from_txt, to_txt in [(msg, cryptotext), (cryptotext, msg)]:
            for i, c in enumerate(from_txt):
                found = False
                if i in used_pos:
                    continue
                if c in except_chars:
                    # 已有替换 (c, *)，或不应被替换
                    iter_found = True
                    found = True
                if found:
                    used_pos.add(i)
                    enigma.reset_pos()
                    enigma.turn_rotor(i + 1)
                    r = enigma.process(c, plugboard=True)
                    if r in except_chars:
                        continue
                    except_chars.add(r)  # r 不应出现在插线板剩余部分
                    if r != to_txt[i]:
                        # 找到了新的替换对
                        t = to_txt[i]
                        except_chars.add(t)
                        new_pair = (t, r) if char_to_index(
                            t) < char_to_index(r) else (r, t)
                        for pair in plugboard:
                            if check_pair_conflict(new_pair, pair):
                                # 与现有对冲突说明不是正解
                                return None
                        plugboard.add(new_pair)
                        enigma.set_plugboard(plugboard)
    return plugboard, except_chars


def pairs_check_dup_letter(pairs: List[Tuple[str, str]]) -> bool:
    """
    检查插线板对是否有重复字母
    这是因为用 combinations() 生成时不会考虑是否有重复字母
    """
    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            if pairs[i].count(pairs[j][0]) or pairs[i].count(pairs[j][1]):
                return True
    return False


async def try_full(msg: str, cryptotext: str,
                   rotor_order: List[int], init_pos: List[int],
                   plugboards: List[Set[Tuple[str, str]]]):
    """
    阶段 2：进一步尝试插线板配置
    """
    if not len(plugboards):
        return [(rotor_order, init_pos, [])]
    enigma = Enigma()
    enigma.init_rotors(rotor_order)
    enigma.set_init_pos(init_pos)
    results = []
    for plugboard in plugboards:
        plugboard = set(filter(lambda p: p[0] != p[1], plugboard))
        ret = extend_plugboard(
            msg, cryptotext, enigma.copy(), plugboard)
        if not ret:
            continue
        plugboard, except_chars = ret
        if len(plugboard) > 6:
            continue
        reduced_alphabet = list(
            filter(lambda c: c not in except_chars, alphabet))
        pairs = list(combinations(reduced_alphabet, 2))  # 所有可能的对
        for left_pairs in combinations(pairs, 6 - len(plugboard)):
            full_plugboard = list(plugboard) + list(left_pairs)
            if pairs_check_dup_letter(full_plugboard):
                continue
            e = enigma.copy()
            e.set_plugboard(full_plugboard)
            encrypt_res = ""
            for c in msg:
                e.turn_rotor(1)
                encrypt_res += e.process(c, plugboard=True)
            if encrypt_res == cryptotext:
                results.append((rotor_order, init_pos, full_plugboard))
    return results


async def main():
    msg: str
    cryptotext: str
    with open("config.txt", "r") as f:
        conf_rows = f.read().splitlines()
        msg = conf_rows[11]
        cryptotext = conf_rows[13]

    rings = find_rings(msg, cryptotext)
    if not len(rings):
        print("没有找到环，破解失败！")

    init_poses = [[x, y, z] for x in range(
        0, 26) for y in range(0, 26) for z in range(0, 26)]

    # 阶段 1
    tasks = []
    for rotor_order in permutations(range(3)):
        for init_pos in init_poses:
            tasks.append(asyncio.create_task(
                try_order_pos(list(rotor_order), init_pos, rings)))
    results = await asyncio.gather(*tasks)
    results = list(filter(lambda x: x is not None, results))

    # 阶段 2
    tasks = []
    for order, init_pos, plugboards in results:
        tasks.append(asyncio.create_task(
            try_full(msg, cryptotext, order, init_pos, plugboards)))
    resultss = await asyncio.gather(*tasks)
    results = [i for rs in resultss for i in rs]

    print("转子顺序\t初始位置\t插线板设置")
    for order, init_pos, plugboard in results:
        o = [i + 1 for i in order]
        ip = [index_to_char(i) for i in init_pos]
        print(f"{o}\t{ip}\t{plugboard}")

if __name__ == "__main__":
    asyncio.run(main())
