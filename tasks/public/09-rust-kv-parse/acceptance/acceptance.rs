use kvparse::{parse, ParseError};

fn pairs(v: &[(&str, &str)]) -> Vec<(String, String)> {
    v.iter().map(|(k, val)| (k.to_string(), val.to_string())).collect()
}

#[test]
fn ordered_pairs_with_comments_and_blanks() {
    let input = "# config\n\nhost = example.com\n  port=8080  \n\n# end\n";
    assert_eq!(parse(input).unwrap(), pairs(&[("host", "example.com"), ("port", "8080")]));
}

#[test]
fn value_may_contain_equals() {
    assert_eq!(parse("q = a=b=c").unwrap(), pairs(&[("q", "a=b=c")]));
}

#[test]
fn empty_value_allowed() {
    assert_eq!(parse("k =").unwrap(), pairs(&[("k", "")]));
}

#[test]
fn missing_equals_reports_line() {
    assert_eq!(parse("a = 1\n\nbad line\n"), Err(ParseError::MissingEquals(3)));
}

#[test]
fn empty_key_reports_line() {
    assert_eq!(parse("a=1\n = 2"), Err(ParseError::EmptyKey(2)));
}

#[test]
fn duplicate_key() {
    assert_eq!(parse("a=1\nb=2\na=3"), Err(ParseError::Duplicate("a".to_string())));
}

#[test]
fn empty_input_is_empty() {
    assert_eq!(parse("").unwrap(), Vec::<(String, String)>::new());
}
