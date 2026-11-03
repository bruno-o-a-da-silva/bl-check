from bl_check.iso6346 import VALUES, check_digit, is_valid


def test_letter_values_skip_multiples_of_eleven() -> None:
    assert (VALUES["A"], VALUES["J"], VALUES["K"], VALUES["U"], VALUES["V"]) == (10, 20, 21,
                                                                                  32, 34)


def test_published_example() -> None:
    # C13 S30 Q28 U32 3 0 5 4 3 8, weights 1, 2, 4 ... 512:
    # 13 + 60 + 112 + 256 + 48 + 0 + 320 + 512 + 768 + 4096 = 6185; 6185 mod 11 = 3.
    assert check_digit("CSQU305438") == 3
    assert is_valid("CSQU3054383")
    assert is_valid("csqu 305438 3")
    assert not is_valid("CSQU3054384")
    assert not is_valid("CSQX3054383")  # category must be U, J or Z
    assert not is_valid("CSQU305438")
