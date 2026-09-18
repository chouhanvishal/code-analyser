#[derive(Debug, PartialEq, Eq)]
pub enum ParseError {
    MissingEquals(usize),
    EmptyKey(usize),
    Duplicate(String),
}

pub fn parse(input: &str) -> Result<Vec<(String, String)>, ParseError> {
    let _ = input;
    todo!()
}
