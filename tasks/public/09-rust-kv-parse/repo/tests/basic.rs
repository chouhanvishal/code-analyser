use kvparse::parse;

#[test]
fn single_pair() {
    let got = parse("a = 1").unwrap();
    assert_eq!(got, vec![("a".to_string(), "1".to_string())]);
}
